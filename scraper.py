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
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # === CDP NETWORK BLOCKER ===
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*evolok*", "*ev-engagement*"]
    })
    
    driver.set_page_load_timeout(180)
    return driver

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
                    if not text or any(x in text for x in ["Related Stories", "| Photo Credit:"]): continue
                    article_content.append({"type": "heading" if el.tag_name == "h4" else "text", "value": text})
                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                if len(article_content) > 1:
                    articles.append({"category": category, "title": title, "url": link, "content": article_content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    finally: driver.quit()
    return articles

def scrape_ie_upsc(pages=20):
    driver = get_driver()
    all_data = []
    base_url = "https://indianexpress.com/section/upsc-current-affairs/page/"
    
    try:
        for p_num in range(1, pages + 1):
            print(f"Scraping IE UPSC Page {p_num}...")
            driver.get(f"{base_url}{p_num}/")
            time.sleep(6)
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
            links = [el.get_attribute("href") for el in elements]

            for link in links:
                try:
                    driver.get(link)
                    time.sleep(5)
                    driver.execute_script("document.querySelectorAll('ev-engagement, .ev-engagement, .ev-paywall-template').forEach(el => el.remove());")
                    
                    title = driver.find_element(By.TAG_NAME, "h1").text.strip()
                    container = driver.find_element(By.ID, "pcl-full-content")
                    
                    if "Daily subject-wise quiz" in title:
                        paras = container.find_elements(By.CSS_SELECTOR, "p, h3")
                        quiz_items = []
                        current_item = None
                        for p in paras:
                            txt = p.text.strip()
                            if not txt: continue
                            if "QUESTION" in txt.upper() or p.tag_name == "h3":
                                if current_item: quiz_items.append(current_item)
                                current_item = {"question": "", "solution": ""}
                            if current_item:
                                if any(x in txt for x in ["Relevance:", "Explanation:", "Therefore, option"]):
                                    current_item["solution"] += f"<p>{txt}</p>"
                                else:
                                    current_item["question"] += f"<p>{txt}</p>"
                        if current_item: quiz_items.append(current_item)
                        all_data.append({"category": "Quizzes", "title": title, "url": link, "quiz_data": quiz_items, "date": datetime.now().strftime("%Y-%m-%d")})
                    else:
                        content_elements = container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                        article_content = [{"type": "text", "value": el.text.strip()} for el in content_elements if el.text.strip() and "Subscriber Only" not in el.text]
                        if len(article_content) > 3:
                            all_data.append({"category": "UPSC Current Affairs", "title": title, "url": link, "content": article_content, "date": datetime.now().strftime("%Y-%m-%d")})
                except: continue
    finally: driver.quit()
    return all_data

# Main Execution
targets = {"Science": "https://www.thehindu.com/sci-tech/science/", "Health": "https://www.thehindu.com/sci-tech/health/", "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/", "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/", "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"}
data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

# Scrape The Hindu
for cat, url in targets.items():
    new_arts = scrape_hindu_section(url, cat)
    urls = [a['url'] for a in full_db]
    for art in new_arts:
        if art['url'] not in urls: full_db.insert(0, art)

# Scrape Indian Express (Current Affairs + Quizzes)
ie_data = scrape_ie_upsc(pages=20)
urls = [a['url'] for a in full_db]
for art in ie_data:
    if art['url'] not in urls: full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:1200], f, ensure_ascii=False, indent=4)
