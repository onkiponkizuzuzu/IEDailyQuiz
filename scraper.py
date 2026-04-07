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
   
    # Network block stops paywalls and trackers natively
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"]
    })
   
    driver.set_page_load_timeout(180)
    return driver

def scrape_macro_economy_deep(base_url):
    driver = get_driver()
    articles = []
    all_links = []
    category = "Macro Economy"
    
    try:
        # Scrape Pages 1 through 9
        for page in range(1, 10):
            page_url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"[{category}] Scanning page {page}/9 → {page_url}")
            driver.get(page_url)
            time.sleep(6)
            
            # If we are on the 9th page, attempt the 5 'Show More' clicks
            if page == 9:
                print(f"  [{category}] Reached page 9. Executing 5 'Show More' clicks...")
                for click_num in range(1, 6):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 800);")
                    time.sleep(2)
                    try:
                        # Covering standard BusinessLine load-more selectors
                        load_more = driver.find_element(By.CSS_SELECTOR, "a.loadMore, .load-more, .show-more, a[title='Load More'], button.loadMore")
                        driver.execute_script("arguments[0].click();", load_more)
                        print(f"    Click {click_num}/5 successful.")
                        time.sleep(4)
                    except Exception as e:
                        print(f"    Click {click_num}/5 failed (reached end of list or button not found).")
                        break
            
            elements = driver.find_elements(By.CSS_SELECTOR, "a.element, h2 a, .title a, .agencySeoClass a")
            current_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href") and "/todays-poll/" not in el.get_attribute("href")]
            all_links.extend(current_links)

        # Remove duplicates
        unique_links = list(set(all_links))
        print(f"\n[{category}] Found {len(unique_links)} total unique links. Proceeding to extract from scratch.")

        # Iterate through all gathered links (not checking against existing_urls because we are replacing them)
        for idx, link in enumerate(unique_links, 1):
            try:
                print(f"  [{idx}/{len(unique_links)}] Extracting: {link}")
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
temp_target = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

print("=== TEMPORARY SCRAPE: Macro Economy (Pages 1-9 + 5 Clicks) ===")
url = temp_target["Macro Economy"]
category = "Macro Economy"

new_arts = scrape_macro_economy_deep(url)

# REPLACEMENT LOGIC: Purge the old Macro Economy articles from the database
original_len = len(full_db)
full_db = [art for art in full_db if art.get('category') != category]
removed_count = original_len - len(full_db)
print(f"\nRemoved {removed_count} old '{category}' articles from the database.")

# Add new articles safely to the top of the database
# Reversing ensures that the newest articles (from page 1) stay at the very top of the JSON
new_arts.reverse()
added_count = 0
for art in new_arts:
    full_db.insert(0, art)
    added_count += 1

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTemporary scrape completed successfully! Added {added_count} brand new articles to data.json.")
