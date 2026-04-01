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
    
    # === CDP NETWORK BLOCKER (The Hindu + Indian Express Paywall) ===
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    
    driver.set_page_load_timeout(180)
    return driver


# ================== The Hindu Scraper (unchanged) ==================
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


# ================== Indian Express Scraper (Paywall Fixed) ==================
def scrape_ie_section(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article/upsc-current-affairs/" in el.get_attribute("href")]))

        for link in links:
            try:
                driver.get(link)
                time.sleep(6)

                # === REMOVE INDIAN EXPRESS PAYWALL ===
                driver.execute_script("""
                    // Remove ev-engagement paywall container
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template').forEach(el => el.remove());
                    // Remove any leftover paywall elements
                    document.querySelectorAll('.paywall-content, [class*="paywall"], [id*="paywall"]').forEach(el => el.remove());
                    // Force show the real content
                    const content = document.getElementById('pcl-full-content');
                    if (content) content.style.display = 'block';
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text:
                        continue
                    if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text",
                        "value": text
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
            except:
                continue
    finally:
        driver.quit()
    return articles


# ================== Indian Express Quizzes Scraper ==================
def scrape_ie_quizzes(category="UPSC Quizzes", pages=20):
    driver = get_driver()
    articles = []
    base_url = "https://indianexpress.com/section/upsc-current-affairs/page/"
    try:
        for page in range(1, pages + 1):
            print(f"Scraping {category} Page {page}...")
            driver.get(f"{base_url}{page}/")
            time.sleep(6)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
            links = []
            for el in elements:
                href = el.get_attribute("href")
                text = el.text
                if href and "/article/upsc-current-affairs/" in href and "Daily subject-wise quiz" in text:
                    links.append(href)
                    
            links = list(set(links))
            
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
                    content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                    
                    article_content = []
                    current_q = None
                    
                    for el in content_elements:
                        text = el.text.strip()
                        if not text:
                            continue
                        if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan", "Click Here", "Share your views"]):
                            continue
                        
                        # Identify new question
                        if "QUESTION" in text.upper() or (el.tag_name in ["h2", "h3"] and "QUESTION" in text.upper()):
                            if current_q:
                                article_content.append(current_q)
                            current_q = {"type": "quiz_item", "question": f"<p><strong>{text}</strong></p>", "solution": ""}
                        elif current_q:
                            # Split logic: if text contains keywords OR if we have already started recording the solution
                            if any(x in text for x in ["Relevance:", "Explanation:", "Therefore, option", "Correct Answer"]) or current_q["solution"] != "":
                                current_q["solution"] += f"<p>{text}</p>"
                            else:
                                current_q["question"] += f"<p>{text}</p>"
                        else:
                            # Intro paragraphs before first question
                            article_content.append({
                                "type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text",
                                "value": text
                            })

                    if current_q:
                        article_content.append(current_q)

                    title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                    
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


# ================== Targets ==================
targets = {
    # The Hindu
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
    
    # Indian Express - UPSC Current Affairs
    "UPSC Current Affairs": "https://indianexpress.com/section/upsc-current-affairs/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

# 1. Scrape standard categories
for cat, url in targets.items():
    print(f"Scraping {cat}...")
    if cat == "UPSC Current Affairs":
        new_arts = scrape_ie_section(url, cat)
    else:
        new_arts = scrape_hindu_section(url, cat)
    
    urls = [a['url'] for a in full_db]
    for art in new_arts:
        if art['url'] not in urls:
            full_db.insert(0, art)

# 2. Scrape Quizzes (20 pages deep)
print("Scraping UPSC Quizzes (20 pages)...")
quiz_arts = scrape_ie_quizzes("UPSC Quizzes", pages=20)
urls = [a['url'] for a in full_db]
for art in quiz_arts:
    if art['url'] not in urls:
        full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:1000], f, ensure_ascii=False, indent=4)

print(f"Scrape completed. Total articles: {len(full_db)}")
