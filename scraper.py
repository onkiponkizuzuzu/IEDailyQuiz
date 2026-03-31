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
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Block Paywall Scripts
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*cxense.com*", "*evolok*", "*ev-engagement*"]
    })
    return driver

def scrape_ie_quizzes():
    driver = get_driver()
    quiz_articles = []
    base_url = "https://indianexpress.com/section/upsc-current-affairs/page/"
    
    try:
        for page in range(1, 21):  # Click 'Next' 20 times
            print(f"Fetching Quiz Page {page}...")
            driver.get(f"{base_url}{page}/")
            time.sleep(5)
            
            # Find articles with "Daily subject-wise quiz" in title
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
            links = [el.get_attribute("href") for el in elements if "Daily subject-wise quiz" in el.text]
            
            for link in links:
                try:
                    driver.get(link)
                    time.sleep(5)
                    
                    # Bypass Paywall via Script
                    driver.execute_script("""
                        document.querySelectorAll('ev-engagement, .ev-engagement, .ev-paywall-template').forEach(el => el.remove());
                        const content = document.getElementById('pcl-full-content');
                        if (content) content.style.display = 'block';
                    """)
                    
                    title = driver.find_element(By.TAG_NAME, "h1").text.strip()
                    container = driver.find_element(By.ID, "pcl-full-content")
                    
                    # Logic to group Question + Relevance + Explanation
                    paras = container.find_elements(By.CSS_SELECTOR, "p, h3")
                    structured_quiz = []
                    current_q = None

                    for p in paras:
                        text = p.text.strip()
                        if not text: continue
                        
                        if "QUESTION" in text.upper() or p.tag_name == "h3":
                            if current_q: structured_quiz.append(current_q)
                            current_q = {"question": "", "solution": ""}
                        
                        if current_q:
                            if any(x in text for x in ["Relevance:", "Explanation:", "Therefore, option"]):
                                current_q["solution"] += f"<p>{text}</p>"
                            else:
                                current_q["question"] += f"<p>{text}</p>"

                    if current_q: structured_quiz.append(current_q)

                    quiz_articles.append({
                        "category": "Quizzes",
                        "title": title,
                        "url": link,
                        "quiz_data": structured_quiz,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                except Exception as e:
                    print(f"Error on quiz page: {e}")
                    continue
    finally:
        driver.quit()
    return quiz_articles

# === Main execution modification ===
# Add "Quizzes": scrape_ie_quizzes() to your loop logic
