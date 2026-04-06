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

# ================== Your existing functions (The Hindu, IE, IE Explained, Quizzes) remain 100% unchanged ==================
# (paste your entire existing scraper.py code here except the targets and main execution part)

# ================== NEW: TH BusinessLine Scraper (incremental) ==================
def scrape_businessline_section(url, category, existing_urls):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        # Scroll to load more
        for _ in range(12):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h2 a, .title a, .agencySeoClass a")
        links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href")]))
        
        new_links = [link for link in links if link not in existing_urls]
        
        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)
                
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

businessline_targets = {
    "Macro Economy": "https://www.thehindubusinessline.com/economy/macro-economy/",
    "Policy": "https://www.thehindubusinessline.com/economy/policy/",
    "Budget 2026": "https://www.thehindubusinessline.com/economy/budget/",
    "Logistics": "https://www.thehindubusinessline.com/economy/logistics/",
    "WEF": "https://www.thehindubusinessline.com/economy/world-economic-forum/",
    "Agri Business": "https://www.thehindubusinessline.com/economy/agri-business/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

# Your existing The Hindu + Indian Express + IE Explained + Quizzes logic (unchanged)
# ... (keep your original code for these)

# NEW: TH BusinessLine
for cat, url in businessline_targets.items():
    print(f"Scraping TH BusinessLine → {cat}...")
    new_arts = scrape_businessline_section(url, cat, existing_urls)
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4)

print(f"Scrape completed. Total articles: {len(full_db)}")
