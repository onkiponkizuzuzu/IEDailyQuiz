import os
import csv
import time
from datetime import datetime
import google_colab_selenium as gs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.colab import files

def get_driver():
    # Properly initialize using google-colab-selenium
    driver = gs.Chrome()
    
    # Block paywall and tracker scripts at the network level
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    
    driver.set_page_load_timeout(180)
    return driver

def load_existing_urls(filepath):
    existing_urls = set()
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'url' in row:
                    existing_urls.add(row['url'])
    return existing_urls

# ================== The Hindu Scraper ==================
def scrape_hindu_section(url, category, existing_urls):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))
        
        new_links = [link for link in links if link not in existing_urls]
        print(f"[{category}] Found {len(new_links)} new articles.")

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(5)

                body_container = driver.find_element(By.CSS_SELECTOR, '[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or "| Photo Credit:" in text or "mukunth.v@" in text or "Related Stories" in text:
                        continue
                    article_content.append(text)

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                if article_content:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": "\n\n".join(article_content),
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                    print(f"  -> Extracted: {title[:50]}...")
            except Exception as e:
                print(f"  -> Failed to extract {link}: {str(e).splitlines()[0]}")
                continue
    finally: driver.quit()
    return articles

# ================== Indian Express Scraper ==================
def scrape_ie_section(url, category, existing_urls):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        # Broadened selectors to catch new IE layouts
        elements = driver.find_elements(By.CSS_SELECTOR, ".articles h2 a, h3.title a, .title a, .img-context h2 a")
        links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article/" in el.get_attribute("href")]))

        new_links = [link for link in links if link not in existing_urls]
        print(f"[{category}] Found {len(new_links)} new articles.")

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)

                # IE Paywall Unhider
                driver.execute_script("""
                    document.querySelectorAll('.ev-engagement, .content-login-wrapper, .ev-paywall-template, .premium-article-ads').forEach(el => el.remove());
                    document.querySelectorAll('.ev-meter-content, .ie-premium-content-block, [class*="paywall"], [id*="paywall"], #pcl-full-content').forEach(el => {
                        el.style.display = 'block';
                        el.style.height = 'auto';
                        el.style.overflow = 'visible';
                        el.style.opacity = '1';
                    });
                """)

                # Strict Schema.org targeting
                body_container = driver.find_element(By.CSS_SELECTOR, '[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or "| Photo Credit:" in text: continue
                    if any(skip in text.lower() for skip in ["subscriber only", "story continues below", "also read", "subscribe"]):
                        continue
                    article_content.append(text)

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                
                if article_content:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": "\n\n".join(article_content),
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                    print(f"  -> Extracted: {title[:50]}...")
            except Exception as e:
                print(f"  -> Failed to extract {link}: {str(e).splitlines()[0]}")
                continue
    finally: driver.quit()
    return articles

# ================== Main Execution ==================
csv_filename = "scraped_data.csv"
existing_urls = load_existing_urls(csv_filename)
all_scraped_articles = []

# Using smaller target list for demonstration
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "UPSC Current Affairs": "https://indianexpress.com/section/upsc-current-affairs/"
}

for cat, url in targets.items():
    print(f"\n--- Scraping {cat} ---")
    if "indianexpress" in url:
        new_arts = scrape_ie_section(url, cat, existing_urls)
    else:
        new_arts = scrape_hindu_section(url, cat, existing_urls)
    
    all_scraped_articles.extend(new_arts)

# ================== CSV Export Routine ==================
if all_scraped_articles:
    file_exists = os.path.isfile(csv_filename)
    
    # Save with utf-8-sig encoding for perfect Excel/CSV compatibility
    with open(csv_filename, 'a', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['category', 'title', 'url', 'content', 'date']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()
            
        for article in all_scraped_articles:
            writer.writerow(article)

    print(f"\n✅ Successfully saved {len(all_scraped_articles)} new articles to {csv_filename}")
    
    # Trigger native Colab download
    files.download(csv_filename)
else:
    print("\nNo new articles to save.")
