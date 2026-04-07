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
   
    # This network block is the real hero. It stops the paywall scripts from ever firing.
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"]
    })
   
    driver.set_page_load_timeout(180)
    return driver

def scrape_macro_economy_temp(base_url, existing_urls):
    driver = get_driver()
    articles = []
    all_links = []
    category = "Macro Economy"
    
    try:
        # Strictly scrape Pages 1, 2, and 3
        for page in range(1, 4):
            page_url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"[{category}] Scanning page {page}/3 → {page_url}")
            driver.get(page_url)
            time.sleep(6)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "a.element, h2 a, .title a, .agencySeoClass a")
            current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href") and "/todays-poll/" not in el.get_attribute("href")]
            all_links.extend(current_links)

        unique_links = list(set(all_links))
        new_links = [link for link in unique_links if link not in existing_urls]
        print(f"\n[{category}] Found {len(unique_links)} total links. {len(new_links)} are new and will be extracted.")

        for idx, link in enumerate(new_links, 1):
            try:
                print(f"  [{idx}/{len(new_links)}] Extracting: {link}")
                driver.get(link)
                time.sleep(5)
                
                # NO JavaScript execution needed. The network block keeps the DOM clean.
                # Targeting the Schema.org container exactly like The Hindu scraper
                body_container = driver.find_element(By.CSS_SELECTOR, 'div[itemprop="articleBody"], .contentbody')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4, h4.sub_head")
               
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:", "Click here"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if el.tag_name.lower() in ["h2", "h3", "h4"] else "text",
                        "value": html_content
                    })

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
               
                if len(article_content) > 1:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                    print(f"      → Success: {title[:50]}...")
                else:
                    print("      → Skipped: Not enough content extracted.")
                    
            except Exception as e:
                print(f"      → Error extracting link: {str(e).splitlines()[0]}")
                continue
                
    finally:
        driver.quit()
        
    return articles

# ================== Temporary Execution ==================
temp_target = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

print("=== TEMPORARY SCRAPE: Macro Economy (Pages 1-3) ===")
url = temp_target["Macro Economy"]
category = "Macro Economy"

new_arts = scrape_macro_economy_temp(url, existing_urls)

added_count = 0
for art in new_arts:
    if art['url'] not in existing_urls:
        full_db.insert(0, art)
        existing_urls.add(art['url'])
        added_count += 1

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary scrape completed successfully! Added {added_count} new articles to data.json.")
