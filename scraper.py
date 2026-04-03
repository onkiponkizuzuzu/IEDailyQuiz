import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================== CONFIG ==================
FULL_SCRAPE = True          # ← Change to False after first successful run
MAX_WORKERS = 4             # Safe limit for GitHub Actions
MAX_ARTICLES_PER_CAT = 150  # For first run only
# ===========================================

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.page_load_strategy = 'eager'

    chrome_options.binary_location = "/usr/bin/google-chrome"
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
                 "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"]
    })
    return driver

# ================== Reusable Scrapers (single driver) ==================
def scrape_hindu_section(driver, url, category):
    articles = []
    try:
        driver.get(url)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.title a")))
        time.sleep(3)
        links = list(set([el.get_attribute("href") for el in driver.find_elements(By.CSS_SELECTOR, "h3.title a") if "/article" in el.get_attribute("href")]))

        for link in links:
            try:
                driver.get(link)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title")))
                time.sleep(3)

                body = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"]')
                els = body.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                content = [{"type": "heading" if e.tag_name == "h4" else "text", "value": e.get_attribute('innerHTML').strip()} 
                           for e in els if e.text.strip() and not any(x in e.text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"])]

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                if len(content) > 1:
                    articles.append({"category": category, "title": title, "url": link, "content": content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    except: pass
    return articles

def scrape_ie_section(driver, url, category):
    # (Same as your previous working IE scraper - kept minimal)
    articles = []
    try:
        driver.get(url)
        time.sleep(6)
        links = list(set([el.get_attribute("href") for el in driver.find_elements(By.CSS_SELECTOR, "h3.title a") if "/article/upsc-current-affairs/" in el.get_attribute("href")]))

        for link in links:
            try:
                driver.get(link)
                time.sleep(5)
                driver.execute_script("""document.querySelectorAll('ev-engagement,.ev-engagement,.content-login-wrapper,.ev-paywall-template,.paywall-content').forEach(el=>el.remove());""")
                body = driver.find_element(By.ID, "pcl-full-content")
                els = body.find_elements(By.CSS_SELECTOR, "p,h2,h3,h4")
                content = [{"type": "heading" if e.tag_name in ["h2","h3","h4"] else "text", "value": e.get_attribute('innerHTML').strip()} 
                           for e in els if e.text.strip() and not any(skip in e.text for skip in ["Subscriber Only","Story continues","ALSO READ","Subscribe","About our expert"])]

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                if len(content) > 3:
                    articles.append({"category": category, "title": title, "url": link, "content": content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    except: pass
    return articles

def scrape_mint_section(driver, url, category):
    articles = []
    try:
        driver.get(url)
        time.sleep(6)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

        links = list(set([el.get_attribute("href") for el in driver.find_elements(By.CSS_SELECTOR, "h2 a, .tagTitle a") if el.get_attribute("href")]))

        for link in links[:40]:
            try:
                driver.get(link)
                time.sleep(5)
                driver.execute_script("document.querySelectorAll('.paywall,.premium,.subscription').forEach(el=>el.remove());")
                body = driver.find_element(By.CSS_SELECTOR, '.premium-article-body, #mainArea')
                els = body.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                content = [{"type": "heading" if e.tag_name in ["h2","h3","h4"] else "text", "value": e.get_attribute('innerHTML').strip()} 
                           for e in els if e.text.strip()]

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                if len(content) > 3:
                    articles.append({"category": category, "title": title, "url": link, "content": content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    except: pass
    return articles

# ================== Main Execution ==================
data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = {a['url'] for a in full_db}

driver = get_driver()

targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
    "UPSC Current Affairs": "https://indianexpress.com/section/upsc-current-affairs/",
    "Global": "https://indianexpress.com/about/explained-global/?ref=explained_pg",
    "Law and Policy": "https://indianexpress.com/section/explained/explained-law/?ref=explained_pg",
    "Sci-Tech": "https://indianexpress.com/about/explained-sci-tech/",
    "Economics": "https://indianexpress.com/about/explained-economics/?ref=explained_pg",
    "Expert Explains": "https://indianexpress.com/about/an-expert-explains/?ref=explained_pg",
    "Everyday Explainer": "https://indianexpress.com/section/explained/everyday-explainers/?ref=explained_pg",
    "Economy": "https://www.livemint.com/economy",
    "MintExplainers": "https://www.livemint.com/topic/mint-explainer",
    "Opinion": "https://www.livemint.com/opinion",
    "Markets": "https://www.livemint.com/market"
}

print("=== Starting scrape ===")
if FULL_SCRAPE:
    print("FULL SCRAPE MODE - Scraping everything")
    max_articles = MAX_ARTICLES_PER_CAT
else:
    print("INCREMENTAL MODE - Only new articles")

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_cat = {}
    for cat, url in targets.items():
        if cat in ["UPSC Current Affairs", "Global", "Law and Policy", "Sci-Tech", "Economics", "Expert Explains", "Everyday Explainer"]:
            future_to_cat[executor.submit(scrape_ie_section, driver, url, cat)] = cat
        elif cat in ["Economy", "MintExplainers", "Opinion", "Markets"]:
            future_to_cat[executor.submit(scrape_mint_section, driver, url, cat)] = cat
        else:
            future_to_cat[executor.submit(scrape_hindu_section, driver, url, cat)] = cat

    for future in as_completed(future_to_cat):
        cat = future_to_cat[future]
        try:
            new_arts = future.result()
            added = 0
            for art in new_arts:
                if art['url'] not in existing_urls:
                    full_db.insert(0, art)
                    existing_urls.add(art['url'])
                    added += 1
            print(f"  → {cat}: {added} new articles")
        except Exception as e:
            print(f"  → {cat}: Error - {e}")

driver.quit()

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:1000], f, ensure_ascii=False, indent=4)

print(f"\nScrape completed. Total articles now: {len(full_db)}")
