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

def scrape_businessline_section(url, category):
    driver = get_driver()
    articles = []
    all_links = []
    
    try:
        print(f"[{category}] Starting full pagination scrape...")
        
        # === Step 1: Scrape pages 1 to 8 ===
        for page in range(1, 9):
            current_url = f"{url}?page={page}" if page > 1 else url
            print(f"[{category}] Scraping page {page}...")
            driver.get(current_url)
            time.sleep(7)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a, .title a, .agencySeoClass a, .element")
            current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]
            all_links.extend(current_links)
        
        # === Step 2: Go to page 9 and click SHOW MORE 20 times ===
        print(f"[{category}] Reaching page 9 and clicking SHOW MORE 20 times...")
        driver.get(f"{url}?page=9")
        time.sleep(8)
        
        for i in range(20):
            try:
                show_more = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.small-link.show-more, [data-show-more]"))
                )
                driver.execute_script("arguments[0].click();", show_more)
                print(f"[{category}] Clicked SHOW MORE {i+1}/20")
                time.sleep(4)
            except:
                print(f"[{category}] No more SHOW MORE button or timeout at click {i+1}")
                break
        
        # Collect final links after all clicks
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a, .title a, .agencySeoClass a, .element")
        final_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]
        all_links.extend(final_links)
        
        # Remove duplicates
        all_links = list(dict.fromkeys(all_links))
        print(f"[{category}] Total unique links found: {len(all_links)}")
        
        # === Step 3: Scrape full content for new articles only ===
        data_file = "data.json"
        full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
        existing_urls = {a['url'] for a in full_db}
        
        new_links = [link for link in all_links if link not in existing_urls]
        print(f"[{category}] Scraping {len(new_links)} new articles...")
        
        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)
                
                # BusinessLine paywall blocker
                driver.execute_script("""
                    document.querySelectorAll('.paywall,.premium,.subscription,#paywallbox,.articleblock-container.readmore').forEach(el => el.remove());
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
            except Exception as e:
                continue
    finally:
        driver.quit()
    
    return articles

# ================== Temporary Targets (only Macro Economy and Policy) ==================
temp_targets = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/",
    "Policy": "https://www.thehindubusinessline.com/economy/policy/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

print("=== TEMPORARY TH BusinessLine FULL SCRAPE (pages 1-8 + 20x SHOW MORE) ===")
for cat, url in temp_targets.items():
    print(f"\nScraping TH BusinessLine → {cat}...")
    new_arts = scrape_businessline_section(url, cat)
    for art in new_arts:
        full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary BusinessLine scrape completed.")
print(f"Added all articles from pages 1-8 + 20× SHOW MORE for Macro Economy and Policy.")
print(f"Total articles now in data.json: {len(full_db)}")
