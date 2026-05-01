from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth
import time
import random
import os

app = Flask(__name__, static_folder='../client', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

def scrape_facebook_group(url, count):
    posts = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth(page)
        
        print(f"Navigating to Group: {url}")
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(5000) # Wait for initial load

        # Try to close popups
        try:
            close_btn = page.query_selector('div[aria-label="Close"]')
            if close_btn: close_btn.click()
        except: pass

        scraped_post_ids = set()
        
        while len(posts) < count:
            # Find all visible post elements
            # Facebook Groups often use role="article" for posts
            post_elements = page.query_selector_all('div[role="article"]')
            
            for element in post_elements:
                if len(posts) >= count:
                    break
                
                # Use inner_text as a rudimentary ID to avoid duplicates
                text_snippet = element.inner_text()[:50]
                if text_snippet in scraped_post_ids:
                    continue
                
                scraped_post_ids.add(text_snippet)
                
                # Extract basic post data
                post_text = ""
                try:
                    text_elem = element.query_selector('div[data-ad-preview="message"]')
                    if text_elem: post_text = text_elem.inner_text()
                    else: post_text = element.inner_text().split('\n')[0] # Fallback
                except: pass

                # Reactions and Comments count
                likes = "0"
                comm_count = "0"
                try:
                    likes_elem = element.query_selector('span[aria-label*="Like"], span[aria-label*="reactions"]')
                    if likes_elem: likes = likes_elem.inner_text().split()[0]
                    
                    comm_elem = element.query_selector('span[aria-label*="comment"]')
                    if comm_elem: comm_count = comm_elem.inner_text().split()[0]
                except: pass

                # Extract visible comments for THIS post
                comments = []
                try:
                    # Look for comment items within this specific post article
                    comment_items = element.query_selector_all('div[role="article"][aria-label*="Comment"]')
                    for c_item in comment_items[:10]: # Limit comments per post
                        try:
                            author = c_item.query_selector('span[dir="auto"] a, span[dir="auto"] strong').inner_text()
                            text = c_item.query_selector('div[dir="auto"]').inner_text()
                            comments.append({"author": author, "text": text})
                        except: pass
                except: pass

                posts.append({
                    "text": post_text,
                    "likes": likes,
                    "comments_count": comm_count,
                    "comments": comments
                })
                print(f"Scraped post {len(posts)}/{count}")

            if len(posts) < count:
                # Scroll down to load more
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(2000)
                
                # Check if we hit a login wall
                if "login" in page.url or page.query_selector('input[name="email"]'):
                    print("Hit login wall. Stopping.")
                    break

        browser.close()
    return posts

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "online"})

@app.route('/api/scrape-group', methods=['POST'])
def scrape_group():
    data = request.json
    url = data.get('url')
    count = data.get('count', 3)
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        posts = scrape_facebook_group(url, count)
        return jsonify({"posts": posts})
    except Exception as e:
        print(f"Scrape Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
