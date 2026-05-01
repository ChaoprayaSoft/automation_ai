from flask import Flask, request, jsonify
from flask_cors import CORS
from apify_client import ApifyClient
import os
import time

app = Flask(__name__, static_folder='../client', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "online", "mode": "apify"})

@app.route('/api/scrape-group', methods=['POST'])
def start_scrape():
    """
    Starts an Apify scrape and returns the run ID immediately.
    This bypasses Render's 30s timeout.
    """
    data = request.json
    url = data.get('url')
    count = data.get('count', 5)
    
    token = os.environ.get('APIFY_API_TOKEN')
    if not token:
        return jsonify({"error": "Apify API Token is missing. Add APIFY_API_TOKEN to Render."}), 403

    client = ApifyClient(token)
    
    try:
        print(f"--- Starting Apify Run for: {url} ---")
        # Start the actor but DON'T wait for it (.start() instead of .call())
        run = client.actor("apify/facebook-groups-scraper").start(run_input={
            "startUrls": [{"url": url}],
            "resultsLimit": count,
            "maxPosts": count,
            "viewOption": "CHRONOLOGICAL",
        })
        
        return jsonify({
            "status": "started",
            "run_id": run["id"]
        })
    except Exception as e:
        print(f"Apify Start Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-status/<run_id>', methods=['GET'])
def check_status(run_id):
    """
    Checks if the Apify run is finished and returns results.
    The frontend polls this every 5 seconds.
    """
    token = os.environ.get('APIFY_API_TOKEN')
    client = ApifyClient(token)
    
    try:
        run = client.run(run_id).get()
        status = run["status"]
        print(f"Run {run_id} status: {status}")
        
        if status == "SUCCEEDED":
            dataset_id = run["defaultDatasetId"]
            posts = []
            group_name = "Facebook Group"
            
            # Process results
            for item in client.dataset(dataset_id).iterate_items():
                text = item.get('text') or item.get('message') or "No text content"
                likes = item.get('likes') or item.get('reactionsCount') or 0
                comms_count = item.get('commentsCount') or 0
                
                if group_name == "Facebook Group" and item.get('groupName'):
                    group_name = item.get('groupName')
                
                raw_comments = item.get('comments') or []
                processed_comments = [{"author": c.get('authorName') or "Anon", "text": c.get('text') or ""} for c in raw_comments[:3]]

                posts.append({
                    "text": text,
                    "likes": str(likes),
                    "comments_count": str(comms_count),
                    "comments": processed_comments
                })
            
            return jsonify({"status": "finished", "group_name": group_name, "posts": posts})
        
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            return jsonify({"status": "failed", "error": f"Scrape job {status.lower()}"})
        
        else:
            # Still running
            return jsonify({"status": "running"})
            
    except Exception as e:
        print(f"Status Check Error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
