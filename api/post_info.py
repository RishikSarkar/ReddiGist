from flask import Flask, Response, request
import os
import json
import re
import praw
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SUBMISSION_ID_REGEX = re.compile(r'/comments/([^/]+)/')

reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent="ReddiGist/1.0"
)

def get_submission_id(url):
    match = SUBMISSION_ID_REGEX.search(url)
    return match.group(1) if match else None

@app.route('/api/post_info', methods=['POST'])
def api_post_info():
    data = json.loads(request.data)
    
    if not data or 'url' not in data:
        return Response(
            json.dumps({"error": "URL is required"}),
            status=400,
            mimetype='application/json'
        )

    submission_id = get_submission_id(data['url'])
    if not submission_id:
        return Response(
            json.dumps({"error": "Invalid Reddit URL"}),
            status=400,
            mimetype='application/json'
        )

    try:
        submission = reddit.submission(id=submission_id)
        
        return Response(
            json.dumps({
                "title": submission.title,
                "numComments": submission.num_comments
            }),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype='application/json'
        )

def handler(request, context):
    return app(request) 