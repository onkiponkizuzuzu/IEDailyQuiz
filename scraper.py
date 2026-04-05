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
        # === Pages 1 to 8 (direct pagination) ===
        for page in range(1, 9):
            page_url = f"{url}?page={page}" if page > 1 else url
            print(f"[{category}] Scraping page {page}/8 → {page_url}")
            driver.get(page_url)
            time.sleep(6)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a, .title a, a.element")
            current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]
            all_links.extend(current_links)
        
        # === Page 9 + Click SHOW MORE 20 times ===
        print(f"[{category}] Going to page 9 and clicking SHOW MORE 20 times...")
        driver.get(f"{url}?page=9")
        time.sleep(8)
        
        for click in range(20):
            try:
                show_more = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.small-link.show-more"))
                )
                driver.execute_script("arguments[0].click();", show_more)
                print(f"[{category}] Clicked SHOW MORE {click+1}/20")
                time.sleep(4)
            except:
                print(f"[{category}] No more 'SHOW MORE' button or end of list.")
                break
        
        # Collect all links after pagination
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a, .title a, a.element")
        current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]
        all_links.extend(current_links)
        
        # Remove duplicates
        unique_links = list(dict.fromkeys(all_links))
        print(f"[{category}] Total unique article links found: {len(unique_links)}")
        
        # === Scrape full content from every link ===
        for link in unique_links:
            try:
                driver.get(link)
                time.sleep(6)
                
                # BusinessLine paywall blocker (same as your existing Hindu scraper)
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

print("=== TEMPORARY TH BusinessLine SCRAPE (All pages 1-8 + 20× SHOW MORE on page 9) ===")
for cat, url in temp_targets.items():
    print(f"\nScraping TH BusinessLine → {cat} ...")
    new_arts = scrape_businessline_section(url, cat)
    for art in new_arts:
        full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary BusinessLine scrape completed.")
print(f"Added ALL articles from pages 1-8 + 20× SHOW MORE for Macro Economy and Policy.")
