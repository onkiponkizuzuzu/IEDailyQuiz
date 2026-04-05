import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_mint_driver():
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
    
    # Notice: *premium* and *paywall* are NOT blocked here, as Mint needs them to load the text payload
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*"]
    })
    
    driver.set_page_load_timeout(180)
    return driver

def scrape_mint_section(url, category, existing_urls):
    driver = get_mint_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        print(f"[{category}] Scrolling to load articles...")
        # Scroll to load articles dynamically
        for _ in range(8):
            driver.execute_script("window.scrollBy(0, 1500);")
            time.sleep(2)
        
        # Broad selectors to catch Mint's layout
        elements = driver.find_elements(By.CSS_SELECTOR, "h2 a, .tagTitle a, .agencySeoClass a, .headline a, .listtostory a")
        links = []
        for el in elements:
            href = el.get_attribute("href")
            if href and "/news/" not in href and href not in links:
                links.append(href)
                
        new_links = [link for link in links if link not in existing_urls]
        print(f"[{category}] Found {len(links)} total links on page, {len(new_links)} are new.")
        
        # Limit to 30 for this test run
        new_links = new_links[:30]

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)
                
                # Unhide Mint's premium content blocks
                driver.execute_script("""
                    document.querySelectorAll('.paywall, .premium, .subscription, [class*="paywall"]').forEach(el => {
                        el.style.display = 'block';
                        el.style.height = 'auto';
                        el.style.overflow = 'visible';
                    });
                """)
                
                # Find the main article container
                try:
                    body_container = driver.find_element(By.CSS_SELECTOR, '.premium-article-body, #mainArea, .storyPage, article, .paywall')
                    content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                except:
                    # Fallback if specific container fails
                    content_elements = driver.find_elements(By.CSS_SELECTOR, "p")

                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    
                    # Filter out short UI text and ads
                    if len(text) < 30 or any(skip in text.lower() for skip in ["subscribe to mint", "catch all the", "download the mint app"]): 
                        continue
                        
                    article_content.append({
                        "type": "heading" if el.tag_name.lower() in ["h2", "h3", "h4"] else "text",
                        "value": html_content
                    })

                title_el = driver.find_elements(By.CSS_SELECTOR, "h1")
                title = title_el[0].text.strip() if title_el else "Mint Article"
                
                if len(article_content) > 2:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                    print(f"  -> SUCCESS: Extracted '{title[:50]}...'")
                else:
                    print(f"  -> SKIPPED: Not enough content extracted from {link}")
                    
            except Exception as e:
                print(f"  -> ERROR extracting {link}: {str(e).splitlines()[0]}")
                continue
                
    finally:
        driver.quit()
    return articles

# ================== Test Execution ==================
# Only testing MintExplainers
test_target = {
    "MintExplainers": "https://www.livemint.com/topic/mint-explainer"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

print("=== TEMPORARY MINT TEST SCRAPE ===")
for cat, url in test_target.items():
    print(f"\nStarting test for → {cat}...")
    new_arts = scrape_mint_section(url, cat, existing_urls)
    
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"\nTest completed. Check your data.json and index.html to verify the articles loaded correctly.")
