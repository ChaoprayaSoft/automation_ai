from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync as stealth
except (ImportError, AttributeError):
    try:
        from playwright_stealth import stealth
    except:
        stealth = None
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
    
    # SMART BYPASS:
    # If we have cookies, use the standard Desktop version (more stable for logged-in sessions)
    # If we DON'T have cookies, use mbasic (most resistant to blocks)
    has_cookies = bool(os.environ.get('FB_COOKIES'))
    
    if not has_cookies:
        if "www.facebook.com" in url:
            url = url.replace("www.facebook.com", "mbasic.facebook.com")
        elif "facebook.com" in url and "mbasic.facebook.com" not in url:
            url = url.replace("facebook.com", "mbasic.facebook.com")
        elif "m.facebook.com" in url:
            url = url.replace("m.facebook.com", "mbasic.facebook.com")
        print(f"No cookies found. Using mbasic bypass.")
    else:
        # If we have cookies, ensure we are on the desktop version if requested
        if "m.facebook.com" in url:
            url = url.replace("m.facebook.com", "www.facebook.com")
        elif "mbasic.facebook.com" in url:
            url = url.replace("mbasic.facebook.com", "www.facebook.com")
        print(f"Cookies detected. Using standard Desktop mode.")
        
    print(f"--- Starting Scrape Process for: {url} ---")
    try:
        with sync_playwright() as p:
            print("Launching Browser...")
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            
            # Default to a TRUSTED Desktop User Agent
            default_desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            user_agent = os.environ.get('USER_AGENT', default_desktop_ua)
            
            # Set up the context
            context_args = {
                "user_agent": user_agent,
                "viewport": {'width': 1280, 'height': 800},
                "locale": "en-US",
                "timezone_id": "UTC"
            }
            
            context = browser.new_context(**context_args)
            
            # --- SMART COOKIE INJECTION ---
            fb_cookies_raw = os.environ.get('FB_COOKIES', '').strip()
            if fb_cookies_raw:
                # Remove common prefixes/suffixes
                if fb_cookies_raw.lower().startswith('cookie:'):
                    fb_cookies_raw = fb_cookies_raw[7:].strip()
                
                print("Injecting session cookies...")
                try:
                    cookie_list = []
                    # More robust parsing for complex cookie strings
                    raw_parts = [p.strip() for p in fb_cookies_raw.split(';') if p.strip()]
                    for pair in raw_parts:
                        if '=' in pair:
                            name, value = pair.split('=', 1)
                            cookie_list.append({
                                "name": name.strip(),
                                "value": value.strip(),
                                "domain": ".facebook.com",
                                "path": "/"
                            })
                    context.add_cookies(cookie_list)
                    print(f"Successfully injected {len(cookie_list)} cookies.")
                except Exception as ce:
                    print(f"Cookie Injection Warning: {ce}")

            page = context.new_page()
            
            # Apply stealth if available
            if stealth and callable(stealth):
                try: stealth(page)
                except: pass
            
            print(f"Navigating to Mobile URL: {url}")
            page.goto(url, wait_until="load", timeout=90000)
            
            print("Page loaded. Checking for redirects...")
            page.wait_for_timeout(5000)
            
            # --- REDIRECT / WRONG PAGE DETECTION ---
            final_url = page.url.lower()
            
            # If redirected to a login page, search page, or generic feed
            if "login" in final_url or "checkpoint" in final_url or "home.php" in final_url:
                print(f"!! REDIRECTED: {final_url}")
                browser.close()
                error_type = "Login Required" if "login" in final_url else "Security Check"
                return {
                    "error": "blocked", 
                    "msg": f"Facebook redirected to a {error_type} page. (Target: {final_url}). Ensure your FB_COOKIES are valid and you are logged in on your browser."
                }
                
            if "/groups/discover" in final_url:
                print(f"!! REDIRECTED to generic feed: {final_url}")
                browser.close()
                return {"error": "redirected", "msg": "Facebook redirected to a generic feed. Try a different group URL."}
            
            # Extract Group Name
            group_name = "Facebook Group"
            try:
                # Try common mobile group name selectors
                gn_elem = page.query_selector('header h3, h1, #header h1, ._673w')
                if gn_elem:
                    group_name = gn_elem.inner_text().strip()
                    print(f"Detected Group Name: {group_name}")
            except: pass

            scraped_post_ids = set()
            max_scrolls = 10
            scroll_count = 0
            
            while len(posts) < count and scroll_count < max_scrolls:
                print(f"Analyzing page (Scroll {scroll_count})...")
                
                # mbasic Facebook selectors are much simpler
                selectors = [
                    'article', 
                    'div[role="article"]',
                    'div._55wo', # mbasic post container
                    'table[role="presentation"]', # Some mbasic posts are in tables
                    'div.story_body_container'
                ]
                
                post_elements = []
                for selector in selectors:
                    found = page.query_selector_all(selector)
                    if len(found) > 0:
                        print(f"Found {len(found)} elements with selector: {selector}")
                        post_elements = found
                        break
                
                for element in post_elements:
                    if len(posts) >= count: break
                    
                    try:
                        # On mbasic, the text is usually in a p or a div
                        # Target specific message areas first
                        content_elem = element.query_selector('div._5pbx, div[dir="auto"], p, div.msg')
                        raw_text = content_elem.inner_text().strip() if content_elem else element.inner_text().strip()
                        
                        if not raw_text or len(raw_text) < 10: continue
                        
                        # SKIP Sponsored or Suggested posts
                        if "Sponsored" in raw_text or "Suggested for you" in raw_text:
                            continue
                        
                        # CLEAN UP: Remove common mbasic UI noise
                        noise_phrases = ["Like · Comment · Share", "Full Story", "More...", "Write a comment...", "·", "React"]
                        clean_text = raw_text
                        for phrase in noise_phrases:
                            clean_text = clean_text.replace(phrase, "")
                        
                        clean_text = clean_text.strip()
                        
                        # Duplicate check
                        text_id = clean_text[:80]
                        if text_id in scraped_post_ids: continue
                        scraped_post_ids.add(text_id)
                        
                        # mbasic likes and comments extraction
                        likes = "0"
                        comms = "0"
                        try:
                            # mbasic uses simple links for these
                            stats_text = element.inner_text()
                            if "Like" in stats_text:
                                import re
                                like_match = re.search(r'Like\s+(\d+)', stats_text)
                                if like_match: likes = like_match.group(1)
                            
                            if "Comment" in stats_text:
                                comm_match = re.search(r'(\d+)\s+Comment', stats_text)
                                if comm_match: comms = comm_match.group(1)
                        except: pass
                        
                        posts.append({
                            "text": clean_text,
                            "likes": likes,
                            "comments_count": comms,
                            "comments": []
                        })
                        print(f"Scraped mbasic post {len(posts)}")
                    except: continue

                if len(posts) >= count: break

                print("Scrolling for more content...")
                page.evaluate("window.scrollBy(0, 1200)")
                page.wait_for_timeout(2000)
                scroll_count += 1

            print(f"Scraping complete: {len(posts)} posts found.")
            browser.close()
            return {"group_name": group_name, "posts": posts}

            scraped_post_ids = set()
            
            # Limit the number of scroll attempts
            max_scrolls = 12
            scroll_count = 0
            
            while len(posts) < count and scroll_count < max_scrolls:
                print(f"Analyzing page (Scroll {scroll_count})...")
                
                # Try multiple selectors for Facebook posts
                post_elements = []
                selectors = [
                    'div[role="article"]',
                    'div[data-testid="fbfeed_story"]',
                    'div[class*="x1y1aw1k"]', # Common FB container class
                    'div.x1lliihq' # Another common container
                ]
                
                for selector in selectors:
                    found = page.query_selector_all(selector)
                    if len(found) > 0:
                        print(f"Found {len(found)} elements with selector: {selector}")
                        post_elements = found
                        break
                
                for element in post_elements:
                    if len(posts) >= count:
                        break
                    
                    try:
                        # Improved duplicate detection
                        inner_text = element.inner_text()
                        if not inner_text: continue
                        
                        text_snippet = inner_text[:100]
                        if text_snippet in scraped_post_ids:
                            continue
                        
                        scraped_post_ids.add(text_snippet)
                        
                        # Extract post text
                        post_text = "No content"
                        text_elem = element.query_selector('div[data-ad-preview="message"], div[dir="auto"]')
                        if text_elem:
                            post_text = text_elem.inner_text()
                        
                        # Reactions
                        likes = "0"
                        try:
                            likes_elem = element.query_selector('span[aria-label*="Like"], span[aria-label*="reactions"]')
                            if likes_elem:
                                likes = likes_elem.inner_text()
                        except: pass

                        # Comments
                        comments = []
                        try:
                            # Try to find comment elements
                            comment_items = element.query_selector_all('div[role="article"][aria-label*="Comment"]')
                            for c_item in comment_items[:5]:
                                try:
                                    author = "User"
                                    author_elem = c_item.query_selector('span[dir="auto"] a, span[dir="auto"] strong')
                                    if author_elem: author = author_elem.inner_text()
                                    
                                    c_text_elem = c_item.query_selector('div[dir="auto"]')
                                    c_text = c_text_elem.inner_text() if c_text_elem else ""
                                    
                                    if c_text:
                                        comments.append({"author": author, "text": c_text})
                                except: pass
                        except: pass

                        posts.append({
                            "text": post_text,
                            "likes": likes,
                            "comments_count": len(comments),
                            "comments": comments
                        })
                        print(f"Successfully scraped post {len(posts)}")
                    except Exception as e:
                        print(f"Error parsing post element: {e}")
                        continue

                if len(posts) < count:
                    print("Scrolling for more...")
                    page.evaluate("window.scrollBy(0, 1000)")
                    page.wait_for_timeout(3000)
                    scroll_count += 1

            print(f"Scrape finished. Total posts: {len(posts)}")
            browser.close()
            return posts
    except Exception as e:
        print(f"CRITICAL ERROR during scraping: {str(e)}")
        raise e

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "online"})

@app.route('/api/scrape-group', methods=['POST'])
def scrape_group():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    url = data.get('url')
    count = data.get('count', 3)
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    print(f"Request received for URL: {url}")
    try:
        result = scrape_facebook_group(url, count)
        
        # Check if the result is an error dict instead of a list of posts
        if isinstance(result, dict) and "error" in result:
            return jsonify({"error": result["msg"]}), 403
            
        return jsonify(result)
    except Exception as e:
        import traceback
        error_msg = f"Backend Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
