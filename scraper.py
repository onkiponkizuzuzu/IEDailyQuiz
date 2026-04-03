import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
   
    chrome_options.binary_location = "/usr/bin/google-chrome"
    service = Service("/usr/bin/chromedriver")
   
    driver = webdriver.Chrome(service=service, options=chrome_options)
   
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
   
    driver.set_page_load_timeout(180)
    return driver

# ================== The Hindu Scraper (reused driver) ==================
def scrape_hindu_section(driver, url, category):
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links:
            try:
                driver.get(link)
                time.sleep(5)

                body_container = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
               
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    article_content.append({"type": "heading" if el.tag_name == "h4" else "text", "value": html_content})

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
               
                if len(article_content) > 1:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except: continue
    except: pass
    return articles

# ================== Indian Express UPSC Current Affairs ==================
def scrape_ie_section(driver, url, category):
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article/upsc-current-affairs/" in el.get_attribute("href")]))

        for link in links:
            try:
                driver.get(link)
                time.sleep(6)

                driver.execute_script("""
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template').forEach(el => el.remove());
                    document.querySelectorAll('.paywall-content, [class*="paywall"], [id*="paywall"]').forEach(el => el.remove());
                    const content = document.getElementById('pcl-full-content');
                    if (content) content.style.display = 'block';
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
               
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    if not text: continue
                    if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan"]):
                        continue
                    article_content.append({"type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text", "value": html_content})

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
               
                if len(article_content) > 3:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except: continue
    except: pass
    return articles

# ================== IE Explained + Load More (incremental) ==================
def scrape_ie_explained_section(driver, url, category, existing_urls):
    articles = []
    try:
        driver.get(url)
        time.sleep(8)

        # Click "Load More" up to 15 times, but stop early if we see already-scraped articles
        for i in range(15):
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, "button.load_tag_data, .m-featured-link.load_tag_data")
                driver.execute_script("arguments[0].click();", load_btn)
                time.sleep(4)
            except:
                break

        elements = driver.find_elements(By.CSS_SELECTOR, "h3 a")
        links = list(set([el.get_attribute("href") for el in elements if "/article/explained/" in el.get_attribute("href")]))

        for link in links:
            if link in existing_urls:  # Stop early on duplicate
                break
            try:
                driver.get(link)
                time.sleep(6)

                driver.execute_script("""
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template').forEach(el => el.remove());
                    document.querySelectorAll('.paywall-content, [class*="paywall"], [id*="paywall"]').forEach(el => el.remove());
                    const content = document.getElementById('pcl-full-content');
                    if (content) content.style.display = 'block';
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
               
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    if not text: continue
                    if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan"]):
                        continue
                    article_content.append({"type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text", "value": html_content})

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
               
                if len(article_content) > 3:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except: continue
    except: pass
    return articles

# ================== Main Execution (single driver + incremental) ==================
data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = {a['url'] for a in full_db}

driver = get_driver()   # ← One driver for everything

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
    "Everyday Explainer": "https://indianexpress.com/section/explained/everyday-explainers/?ref=explained_pg"
}

for cat, url in targets.items():
    print(f"Scraping {cat}...")
    if cat == "UPSC Current Affairs":
        new_arts = scrape_ie_section(driver, url, cat)
    elif cat in ["Global", "Law and Policy", "Sci-Tech", "Economics", "Expert Explains", "Everyday Explainer"]:
        new_arts = scrape_ie_explained_section(driver, url, cat, existing_urls)
    else:
        new_arts = scrape_hindu_section(driver, url, cat)
    
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)
            existing_urls.add(art['url'])

driver.quit()   # Close the single driver at the end

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:1000], f, ensure_ascii=False, indent=4)

print(f"Scrape completed. Total articles: {len(full_db)}")
