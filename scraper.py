import time
import json
import pandas as pd
import google_colab_selenium as gs
from selenium.webdriver.common.by import By
from google.colab import files

def get_colab_driver():
    # Initialize the driver manager
    driver = gs.Chrome()
    
    # CDP Network Blocker
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    driver.set_page_load_timeout(180)
    return driver

def scrape_ie_quizzes():
    driver = get_colab_driver()
    quiz_links = []
    
    # --- STEP 1: Pagination & Link Collection ---
    driver.get("https://indianexpress.com/section/upsc-current-affairs/")
    time.sleep(5)
    
    for _ in range(20):
        # Grab all quiz links on the current page
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        for el in elements:
            try:
                title = el.get_attribute("title") or el.text
                if "Daily subject-wise quiz" in title:
                    quiz_links.append(el.get_attribute("href"))
            except:
                continue
                
        # Click the 'Next' button to paginate
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers")
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(6)
        except:
            break  # No more pages

    quiz_links = list(set(quiz_links))
    print(f"Found {len(quiz_links)} quiz articles. Starting extraction...")
    
    # --- STEP 2: Content Extraction ---
    quiz_data = []
    
    for url in quiz_links:
        try:
            driver.get(url)
            time.sleep(5)
            
            # Remove Evolok/Paywall DOM elements
            driver.execute_script("""
                document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template, .paywall-content').forEach(el => el.remove());
                const content = document.getElementById('pcl-full-content');
                if (content) content.style.display = 'block';
            """)
            
            body = driver.find_element(By.ID, "pcl-full-content")
            elements = body.find_elements(By.CSS_SELECTOR, "p, h3")
            title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
            
            questions = []
            current_q = None
            
            for el in elements:
                text = el.text.strip()
                
                # Clean specific patterns and empty strings
                if not text or "| Photo Credit:" in text:
                    continue
                    
                # Identify Question Start
                if "QUESTION" in text and el.tag_name == "h3":
                    if current_q:
                        questions.append(current_q)
                    current_q = {"question": text, "options": [], "solution": []}
                    
                elif current_q:
                    # Identify Options
                    if text.startswith("(a)") or text.startswith("(b)") or text.startswith("(c)") or text.startswith("(d)"):
                        current_q["options"].append(text)
                    # Identify Solution/Explanation
                    elif "Relevance:" in text or "Explanation:" in text or "Therefore, option" in text or text.startswith("—"):
                        current_q["solution"].append(text)
                    # Append multi-line question text
                    elif text and not current_q["options"] and not current_q["solution"]:
                        current_q["question"] += "\n" + text
                        
            if current_q:
                questions.append(current_q)
                
            if questions:
                quiz_data.append({
                    "category": "UPSC Quizzes",
                    "title": title,
                    "url": url,
                    "questions": questions,
                    "date": pd.Timestamp.now().strftime("%Y-%m-%d")
                })
        except Exception as e:
            print(f"Skipping {url}: {e}")
            continue

    driver.quit()
    
    # --- STEP 3: Export Routines ---
    # Save to JSON for HTML UI
    with open("quiz_data.json", "w", encoding="utf-8") as f:
        json.dump(quiz_data, f, ensure_ascii=False, indent=4)
        
    # Save to CSV and trigger download
    df = pd.DataFrame(quiz_data)
    df.to_csv("upsc_quizzes.csv", encoding="utf-8-sig", index=False)
    files.download("upsc_quizzes.csv")
    
    print("Scraping complete. Files downloaded.")

# Run the function
scrape_ie_quizzes()
