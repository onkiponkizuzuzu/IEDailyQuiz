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
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
   
    chrome_options.binary_location = "/usr/bin/google-chrome"
    service = Service("/usr/bin/chromedriver")
   
    driver = webdriver.Chrome(service=service, options=chrome_options)
   
    # Block external paywall/tracker scripts to keep the DOM clean
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"]
    })
   
    driver.set_page_load_timeout(180)
    return driver

def scrape_businessline_temp(base_url, category, existing_urls):
    driver = get_driver()
    articles = []
    all_links = []
    
    try:
        # Scrape Pages 1 through 9
        for page in range(1, 10):
            page_url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"[{category}] Scanning page {page}/9 → {page_url}")
            driver.get(page_url)
            time.sleep(6)
            
            # If on page 9, perform 5 "Show More" clicks/scrolls
            if page == 9:
                print(f"[{category}] Reached page 9. Executing 5 'Show More' actions...")
                for i in range(5):
                    try:
                        # Attempt to click 'Show More' if it exists
                        btn = driver.find_element(By.CSS_SELECTOR, ".loadMoreBtn, a.show-more, button.show-more, .btn-load-more")
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                    except:
                        # Fallback to scrolling to trigger infinite load
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "a.element, h2 a, .title a, .agencySeoClass a")
            current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href") and "/todays-poll/" not in el.get_attribute("href")]
            all_links.extend(current_links)

        unique_links = list(set(all_links))
        new_links = [link for link in unique_links if link not in existing_urls]
        print(f"\n[{category}] Found {len(unique_links)} total links. {len(new_links)} will be extracted.")

        for idx, link in enumerate(new_links, 1):
            try:
                print(f"  [{idx}/{len(new_links)}] Extracting: {link}")
                driver.get(link)
                time.sleep(5)
                
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
temp_targets = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/",
    "Policy": "https://www.thehindubusinessline.com/economy/policy/",
    "WEF": "https://www.thehindubusinessline.com/economy/world-economic-forum/",
    "Budget 2026": "https://www.thehindubusinessline.com/economy/budget/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

# 1. PURGE existing articles for these specific subtopics to start from scratch
categories_to_replace = list(temp_targets.keys())
original_count = len(full_db)
full_db = [art for art in full_db if art.get('category') not in categories_to_replace]
removed_count = original_count - len(full_db)

print(f"=== TEMPORARY SCRAPE: TH BusinessLine Deep Dive ===")
print(f"Removed {removed_count} old articles from {categories_to_replace} to start fresh.\n")

existing_urls = set(a['url'] for a in full_db)
total_added = 0

# 2. SCRAPE and INSERT new articles
for cat, url in temp_targets.items():
    print(f"\n--- Starting {cat} ---")
    new_arts = scrape_businessline_temp(url, cat, existing_urls)
    
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)
            existing_urls.add(art['url'])
            total_added += 1

# 3. SAVE database safely
with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:8000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary scrape completed successfully! Added {total_added} brand new articles.")
