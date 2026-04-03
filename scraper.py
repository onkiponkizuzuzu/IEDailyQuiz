import os
import json
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

FULL_SCRAPE = True          # ← Change to False AFTER first successful full run
MAX_WORKERS = 4
MAX_MINT_FIRST_RUN = 50     # Mint will scrape 50 articles per subtopic on first run

# --- Your exact scraping functions remain completely unchanged ---

def scrape_hindu(driver, url, category):
    articles = []
    try:
        driver.goto(url, wait_until="domcontentloaded")
        driver.wait_for_selector("h3.title a", timeout=15000)
        links = list(set([a.get_attribute("href") for a in driver.query_selector_all("h3.title a") if "/article" in a.get_attribute("href")]))

        for link in links:
            try:
                driver.goto(link, wait_until="domcontentloaded")
                driver.wait_for_selector("h1.title", timeout=10000)
                
                body = driver.query_selector('div.schemaDiv[itemprop="articleBody"]')
                elements = body.query_selector_all("p, h4.sub_head") if body else []
                
                content = []
                for el in elements:
                    text = el.inner_text().strip()
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    content.append({"type": "heading" if el.get_attribute("tagName").lower() == "h4" else "text", "value": el.inner_html().strip()})

                title = driver.query_selector("h1.title").inner_text().strip()
                if len(content) > 1:
                    articles.append({"category": category, "title": title, "url": link, "content": content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    except: pass
    return articles

def scrape_ie(driver, url, category):
    articles = []
    try:
        driver.goto(url, wait_until="domcontentloaded")
        driver.wait_for_selector("h3.title a", timeout=15000)
        links = list(set([a.get_attribute("href") for a in driver.query_selector_all("h3.title a") if "/article/upsc-current-affairs/" in a.get_attribute("href")]))

        for link in links:
            try:
                driver.goto(link, wait_until="domcontentloaded")
                # Paywall removal
                driver.evaluate("""() => {
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template, .paywall-content').forEach(el => el.remove());
                    const c = document.getElementById('pcl-full-content');
                    if (c) c.style.display = 'block';
                }""")
                
                body = driver.query_selector("#pcl-full-content")
                elements = body.query_selector_all("p, h2, h3, h4") if body else []
                
                content = []
                for el in elements:
                    text = el.inner_text().strip()
                    if not text: continue
                    if any(skip in text for skip in ["Subscriber Only", "Story continues below this ad", "ALSO READ", "Subscribe", "About our expert", "Select a plan"]):
                        continue
                    content.append({"type": "heading" if el.get_attribute("tagName").lower() in ["h2","h3","h4"] else "text", "value": el.inner_html().strip()})

                title = driver.query_selector("h1").inner_text().strip()
                if len(content) > 3:
                    articles.append({"category": category, "title": title, "url": link, "content": content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    except: pass
    return articles

def scrape_mint(driver, url, category, existing_urls):
    articles = []
    try:
        driver.goto(url, wait_until="domcontentloaded")
        driver.wait_for_selector("h2 a, .tagTitle a", timeout=15000)

        # Scroll to load more
        for _ in range(8):
            driver.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)

        elements = driver.query_selector_all("h2 a, .tagTitle a")
        links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href")]))

        limit = MAX_MINT_FIRST_RUN if FULL_SCRAPE else 999
        for link in links[:limit]:
            if link in existing_urls and not FULL_SCRAPE:
                break
            try:
                driver.goto(link, wait_until="domcontentloaded")
                driver.evaluate("""() => {
                    document.querySelectorAll('.paywall,.premium,.subscription').forEach(el => el.remove());
                }""")
                
                body = driver.query_selector('.premium-article-body, #mainArea')
                elements = body.query_selector_all("p, h2, h3, h4") if body else []
                
                content = []
                for el in elements:
                    text = el.inner_text().strip()
                    if not text: continue
                    content.append({"type": "heading" if el.get_attribute("tagName").lower() in ["h2","h3","h4"] else "text", "value": el.inner_html().strip()})

                title = driver.query_selector("h1").inner_text().strip()
                if len(content) > 3:
                    articles.append({"category": category, "title": title, "url": link, "content": content, "date": datetime.now().strftime("%Y-%m-%d")})
            except: continue
    except: pass
    return articles


# ================== NEW PARALLEL WORKER ==================
def process_category(cat, url, target_type, existing_urls):
    """
    This function runs in a completely separate CPU process. 
    It launches its own isolated browser so it doesn't collide with other categories.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        driver = context.new_page()
        
        try:
            if target_type == "ie":
                return cat, scrape_ie(driver, url, cat)
            elif target_type == "mint":
                return cat, scrape_mint(driver, url, cat, existing_urls)
            else:
                return cat, scrape_hindu(driver, url, cat)
        except Exception as e:
            return cat, {"error": str(e)}
        finally:
            browser.close()


# ================== Main Execution ==================
# Note: if __name__ == '__main__': is strictly required for Python Multiprocessing
if __name__ == '__main__':
    data_file = "data.json"
    full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
    existing_urls = {a['url'] for a in full_db}

    targets = {
        "Science": "https://www.thehindu.com/sci-tech/science/",
        "Health": "https://www.thehindu.com/sci-tech/health/",
        "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
        "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
        "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
        "UPSC Current Affairs": "https://indianexpress.com/section/upsc-current-affairs/",
        "Global": "https://indianexpress.com/about/explained-global/?ref=explained_pg",
        "Law and Policy": "https://indianexpress.com/section/explained/explained-law/?ref=explained_pg",
        "Sci-Tech": "https://indianexpress.com/about/explained-sci-tech/",
        "Economics": "https://indianexpress.com/about/explained-economics/?ref=explained_pg",
        "Expert Explains": "https://indianexpress.com/about/an-expert-explains/?ref=explained_pg",
        "Everyday Explainer": "https://indianexpress.com/section/explained/everyday-explainers/?ref=explained_pg",
        "Economy": "https://www.livemint.com/economy",
        "MintExplainers": "https://www.livemint.com/topic/mint-explainer",
        "Opinion": "https://www.livemint.com/opinion",
        "Markets": "https://www.livemint.com/market"
    }

    # Prepare the arguments for our parallel processes
    tasks_args = []
    for cat, url in targets.items():
        if cat in ["UPSC Current Affairs", "Global", "Law and Policy", "Sci-Tech", "Economics", "Expert Explains", "Everyday Explainer"]:
            tasks_args.append((cat, url, "ie", existing_urls))
        elif cat in ["Economy", "MintExplainers", "Opinion", "Markets"]:
            tasks_args.append((cat, url, "mint", existing_urls))
        else:
            tasks_args.append((cat, url, "hindu", existing_urls))

    print(f"Starting parallel scrape with {MAX_WORKERS} workers...")
    
    # ProcessPoolExecutor safely isolates Playwright instances across CPU cores
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_category, *args) for args in tasks_args]
        
        for future in as_completed(futures):
            cat, result = future.result()
            
            # Check if the process returned an error dictionary
            if isinstance(result, dict) and "error" in result:
                print(f"  → {cat}: Failed due to error - {result['error']}")
                continue
                
            added = 0
            for art in result:
                if art['url'] not in existing_urls:
                    full_db.insert(0, art)
                    existing_urls.add(art['url'])
                    added += 1
            print(f"  → {cat}: {added} new articles processed.")

    with open(data_file, "w", encoding='utf-8') as f:
        json.dump(full_db[:1000], f, ensure_ascii=False, indent=4)

    print(f"Scrape completed. Total articles in database: {len(full_db)}")
