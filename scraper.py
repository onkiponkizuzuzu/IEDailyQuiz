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

def scrape_businessline_section(url, category, existing_urls):
    driver = get_driver()
    all_links = []
    try:
        print(f"[{category}] Scraping pages 1-8...")
        for page in range(1, 9):
            current_url = url + (f"?page={page}" if page > 1 else "")
            driver.get(current_url)
            time.sleep(6)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "a.element, h3.title a, .title a")
            current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]
            all_links.extend(current_links)
            print(f"  → Page {page}: {len(current_links)} articles found")

        # Now page 9 + Show More 10 times
        print(f"[{category}] Going to page 9 and clicking SHOW MORE 10 times...")
        driver.get(url + "?page=9" if "?page=9" else url)
        time.sleep(6)
        
        for click in range(10):
            try:
                show_more = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.small-link.show-more"))
                )
                driver.execute_script("arguments[0].click();", show_more)
                print(f"  → Clicked SHOW MORE {click+1}/10")
                time.sleep(4)
            except:
                print("  → No more SHOW MORE button")
                break

        # Final extraction after Show More
        elements = driver.find_elements(By.CSS_SELECTOR, "a.element, h3.title a, .title a")
        final_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]
        all_links.extend(final_links)
        
        all_links = list(set(all_links))  # remove duplicates
        new_links = [link for link in all_links if link not in existing_urls]
        print(f"[{category}] Found {len(new_links)} NEW articles to scrape")

        articles = []
        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)
                
                # BusinessLine paywall blocker
                driver.execute_script("""
                    document.querySelectorAll('.paywall,.premium,.subscription').forEach(el => el.remove());
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

# ================== TEMPORARY TARGETS (only Macro Economy + Policy) ==================
temp_targets = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/",
    "Policy": "https://www.thehindubusinessline.com/economy/policy/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

print("=== TEMPORARY TH BUSINESSLINE SCRAPE (Pages 1-8 + 10× SHOW MORE) ===")
for cat, url in temp_targets.items():
    print(f"Scraping TH BusinessLine → {cat}...")
    new_arts = scrape_businessline_section(url, cat, existing_urls)
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary BusinessLine scrape completed.\nAdded all articles from pages 1-8 + 10× Show More on page 9.\nTotal articles in data.json now: {len(full_db)}")
