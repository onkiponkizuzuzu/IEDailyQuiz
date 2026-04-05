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
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"]
    })
   
    driver.set_page_load_timeout(180)
    return driver

# ================== Mint Scraper (30 articles per subtopic) ==================
def scrape_mint_section(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        # Scroll to load more articles
        for _ in range(12):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h2 a, .tagTitle a, .agencySeoClass a")
        links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href")]))
        
        # Limit to 30 articles only
        for link in links[:30]:
            try:
                driver.get(link)
                time.sleep(6)
                
                # Mint paywall blocker
                driver.execute_script("""
                    document.querySelectorAll('.paywall,.premium,.subscription').forEach(el => el.remove());
                """)
                
                body_container = driver.find_element(By.CSS_SELECTOR, '.premium-article-body, #mainArea')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
               
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    if not text: continue
                    article_content.append({
                        "type": "heading" if el.tag_name.lower() in ["h2", "h3", "h4"] else "text",
                        "value": html_content
                    })

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
    finally:
        driver.quit()
    return articles

# ================== Mint Targets ==================
mint_targets = {
    "Economy": "https://www.livemint.com/economy",
    "MintExplainers": "https://www.livemint.com/topic/mint-explainer",
    "Opinion": "https://www.livemint.com/opinion",
    "Markets": "https://www.livemint.com/market"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

print("=== TEMPORARY MINT FULL SCRAPE (30 articles per subtopic) ===")
for cat, url in mint_targets.items():
    print(f"Scraping Mint → {cat} (max 30 articles)...")
    new_arts = scrape_mint_section(url, cat)
    for art in new_arts:
        full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary Mint scrape completed. Added articles from Mint only.")
