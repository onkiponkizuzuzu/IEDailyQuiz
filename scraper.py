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
    
    # === CDP NETWORK BLOCKER ===
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    
    driver.set_page_load_timeout(180)
    return driver

# ================== The Hindu Scraper (Unchanged) ==================
def scrape_hindu_section(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links:
            try:
                driver.get(link)
                time.sleep(5)

                body_container = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if el.tag_name == "h4" else "text",
                        "value": text
                    })

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                if len(article_content) > 1:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except:
                continue
    finally:
        driver.quit()
    return articles

# ================== Indian Express Quiz Scraper ==================
def scrape_ie_quizzes(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        # Filter strictly for Quiz articles
        links = list(set([el.get_attribute("href") for el in elements if "UPSC Essentials | Daily subject-wise quiz :" in el.get_attribute("title")]))

        for link in links:
            try:
                driver.get(link)
                time.sleep(6)

                # === REMOVE INDIAN EXPRESS PAYWALL ===
                driver.execute_script("""
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template').forEach(el => el.remove());
                    document.querySelectorAll('.paywall-content, [class*="paywall"], [id*="paywall"]').forEach(el => el.remove());
                    const content = document.getElementById('pcl-full-content');
                    if (content) content.style.display = 'block';
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h3")
                
                article_content = []
                current_block = None

                for el in content_elements:
                    text = el.text.strip()
                    if not text:
                        continue
                    if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "Stay updated", "Click Here", "Previous Daily Subject-Wise-Quiz"]):
                        continue
                    
                    # Group text into Question/Solution pairs
                    if text.upper().startswith("QUESTION"):
                        if current_block:
                            article_content.append(current_block)
                        current_block = {"type": "quiz_item", "question": text + "\n", "solution": ""}
                    elif current_block is not None:
                        # Check if we've reached the explanation/solution part
                        if text.startswith("Relevance:") or text.startswith("Explanation:") or "is the correct answer" in text.lower():
                            current_block["solution"] += text + "\n\n"
                        else:
                            if not current_block["solution"]:
                                # Still part of the question/options
                                current_block["question"] += text + "\n"
                            else:
                                # Part of a multi-paragraph explanation
                                current_block["solution"] += text + "\n\n"

                if current_block:
                    article_content.append(current_block)

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                
                if len(article_content) > 0:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                print(f"Error scraping quiz {link}: {e}")
                continue
    finally:
        driver.quit()
    return articles

# ================== Targets ==================
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
    "UPSC Quizzes": "https://indianexpress.com/section/upsc-current-affairs/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

for cat, url in targets.items():
    print(f"Scraping {cat}...")
    if cat == "UPSC Quizzes":
        new_arts = scrape_ie_quizzes(url, cat)
    else:
        new_arts = scrape_hindu_section(url, cat)
    
    urls = [a['url'] for a in full_db]
    for art in new_arts:
        if art['url'] not in urls:
            full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:1000], f, ensure_ascii=False, indent=4)

print(f"Scrape completed. Total articles: {len(full_db)}")
