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
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    
    driver.set_page_load_timeout(180)
    return driver

# ================== The Hindu Scraper ==================
def scrape_hindu_section(url, category, existing_urls):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))
        
        # Incremental check: Only process links we haven't scraped yet
        new_links = [link for link in links if link not in existing_urls]

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(5)

                body_container = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    
                    article_content.append({"type": "heading" if el.tag_name == "h4" else "text", "value": html_content})

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                if len(article_content) > 1:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except: continue
    finally: driver.quit()
    return articles

# ================== Regular Indian Express Scraper ==================
def scrape_ie_section(url, category, existing_urls):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if "/article/upsc-current-affairs/" in el.get_attribute("href")]))

        # Incremental check
        new_links = [link for link in links if link not in existing_urls]

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)

                driver.execute_script("""
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template').forEach(el => el.remove());
                    document.querySelectorAll('.paywall-content, [class*="paywall"], [id*="paywall"]').forEach(el => el.remove());
                    const content = document.getElementById('pcl-full-content');
                    if (content) content.style.display = 'block';
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    
                    if not text: continue
                    if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan"]):
                        continue
                    
                    article_content.append({"type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text", "value": html_content})

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
    finally: driver.quit()
    return articles

# ================== IE Explained Scraper (Incremental + 30 Limit) ==================
def scrape_ie_explained(url, category, existing_urls, is_first_run):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(5)

        clicks = 0
        max_clicks = 15
        all_links = []

        while clicks < max_clicks:
            elements = driver.find_elements(By.CSS_SELECTOR, "#tag_article .details h3 a")
            # Use set to remove duplicates, then convert to list
            current_links = list(set([el.get_attribute("href") for el in elements if "/article/explained/" in el.get_attribute("href")]))
            all_links = current_links

            if is_first_run:
                # If first run for this subtopic, stop clicking once we have ~30 links
                if len(all_links) >= 30:
                    break
            else:
                # If incremental run, stop clicking immediately if we see ANY link we already have
                if any(link in existing_urls for link in current_links):
                    break

            try:
                load_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "load_tag_article"))
                )
                driver.execute_script("arguments[0].click();", load_more)
                clicks += 1
                print(f"[{category}] Clicked Load More {clicks}")
                time.sleep(3)
            except:
                break # No more button found

        # Filter to only get links not in DB
        new_links = [link for link in all_links if link not in existing_urls]

        # Enforce exact 30 limit on first run
        if is_first_run:
            new_links = new_links[:30]

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(5)

                driver.execute_script("""
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template, .ev-meter-content').forEach(el => el.remove());
                    document.querySelectorAll('.paywall-content, [class*="paywall"], [id*="paywall"]').forEach(el => el.remove());
                    const content = document.getElementById('pcl-full-content');
                    if (content) content.style.display = 'block';
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or any(skip in text for skip in ["Subscriber Only", "Story continues below", "ALSO READ", "Subscribe"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text",
                        "value": el.get_attribute('innerHTML').strip()
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
    finally: driver.quit()
    return articles

# ================== Indian Express Quizzes Scraper ==================
def scrape_ie_quizzes(category, existing_urls, pages=20):
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
                if href and "/article/upsc-current-affairs/" in href and "Daily subject-wise quiz" in el.text:
                    links.append(href)
                    
            links = list(set(links))
            new_links = [link for link in links if link not in existing_urls]

            # Stop paginating if all quizzes on this page are already in our database
            if links and not new_links:
                print("Reached already scraped quizzes. Stopping pagination.")
                break
            
            for link in new_links:
                try:
                    driver.get(link)
                    time.sleep(6)

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
                        html_content = el.get_attribute('innerHTML').strip()
                        
                        if not text: continue
                        if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan", "Click Here", "Share your views"]):
                            continue
                        
                        if "QUESTION" in text.upper() or (el.tag_name in ["h2", "h3"] and "QUESTION" in text.upper()):
                            if current_q: article_content.append(current_q)
                            current_q = {"type": "quiz_item", "question": f"<p>{html_content}</p>", "solution": ""}
                        elif current_q:
                            if any(x in text for x in ["Relevance:", "Explanation:", "Therefore, option", "Correct Answer", "Answer:"]) or current_q["solution"] != "":
                                current_q["solution"] += f"<p>{html_content}</p>"
                            else:
                                current_q["question"] += f"<p>{html_content}</p>"
                        else:
                            article_content.append({"type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text", "value": html_content})

                    if current_q: article_content.append(current_q)
                    title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                    
                    if len(article_content) > 1:
                        articles.append({
                            "category": category,
                            "title": title,
                            "url": link,
                            "content": article_content,
                            "date": datetime.now().strftime("%Y-%m-%d")
                        })
                except: continue
    finally: driver.quit()
    return articles

# ================== Targets & Main Execution ==================
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
    "UPSC Current Affairs": "https://indianexpress.com/section/upsc-current-affairs/"
}

ie_explained_targets = {
    "Global": "https://indianexpress.com/about/explained-global/?ref=explained_pg",
    "Sci-Tech": "https://indianexpress.com/about/explained-sci-tech/",
    "Economics": "https://indianexpress.com/about/explained-economics/?ref=explained_pg",
    "Expert Explains": "https://indianexpress.com/about/an-expert-explains/?ref=explained_pg",
    "Everyday Explainer": "https://indianexpress.com/section/explained/everyday-explainers/?ref=explained_pg",
    "Law and Policy": "https://indianexpress.com/section/explained/explained-law/?ref=explained_pg"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []

# Create a fast lookup set of URLs we already have
existing_urls = set(a['url'] for a in full_db)

# Process Main Targets
for cat, url in targets.items():
    print(f"Scraping {cat}...")
    new_arts = scrape_ie_section(url, cat, existing_urls) if cat == "UPSC Current Affairs" else scrape_hindu_section(url, cat, existing_urls)
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

# Process IE Explained Targets
for cat, url in ie_explained_targets.items():
    print(f"Scraping IE Explained: {cat}...")
    
    # Check if THIS specific category already has entries in the database
    existing_category_count = sum(1 for a in full_db if a.get('category') == cat)
    is_first_run = existing_category_count == 0
    
    new_arts = scrape_ie_explained(url, cat, existing_urls, is_first_run)
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

# Process Quizzes
print("Scraping UPSC Quizzes...")
quiz_arts = scrape_ie_quizzes("UPSC Quizzes", existing_urls, pages=20)
for art in quiz_arts:
    full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:2500], f, ensure_ascii=False, indent=4) 

print(f"Scrape completed. Total articles in database: {len(full_db)}")
