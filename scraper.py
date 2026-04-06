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
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"]
    })
   
    driver.set_page_load_timeout(180)
    return driver

def scrape_businessline_section(url, category):
    driver = get_driver()
    articles = []
    try:
        for page in range(1, 9):   # ← Pages 1 to 8 only
            page_url = url if page == 1 else f"{url}?page={page}"
            print(f"[{category}] Scraping page {page}/8 → {page_url}")
            driver.get(page_url)
            time.sleep(7)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "a.element, h2 a, .title a, .agencySeoClass a")
            links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]))
            
            for link in links:
                try:
                    driver.get(link)
                    time.sleep(6)
                    
                    # BusinessLine paywall blocker (same as The Hindu pattern)
                    driver.execute_script("""
                        document.querySelectorAll('.paywall,.premium,.subscription,.articleblock-container.readmore').forEach(el => el.remove());
                        const main = document.querySelector('#ControlPara, .contentbody');
                        if (main) main.style.display = 'block';
                    """)
                    
                    body_container = driver.find_element(By.CSS_SELECTOR, '#ControlPara, .contentbody')
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

# ================== Temporary Targets (only 2 subtopics) ==================
temp_targets = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/",
    "Policy": "https://www.thehindubusinessline.com/economy/policy/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

print("=== TEMPORARY TH BusinessLine SCRAPE (All articles from pages 1-8) ===")
for cat, url in temp_targets.items():
    print(f"Scraping TH BusinessLine → {cat}...")
    new_arts = scrape_businessline_section(url, cat)
    
    # Only add articles that are not already in data.json
    added = 0
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)      # ← newest on top
            existing_urls.add(art['url'])
            added += 1
    print(f"   → Added {added} new articles for {cat}")

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary scrape completed. data.json updated safely (existing content preserved).")
