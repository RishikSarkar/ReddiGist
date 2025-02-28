from flask import Flask, Response, request, jsonify
import os
import json
import re
import praw
from dotenv import load_dotenv

load_dotenv()

# Regular expression to extract submission ID
SUBMISSION_ID_REGEX = re.compile(r'/comments/([^/]+)/')

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent="ReddiGist/1.0"
)

def get_submission_id(url):
    match = SUBMISSION_ID_REGEX.search(url)
    return match.group(1) if match else None

def handler(request):
    # Extract request data
    try:
        data = json.loads(request.body)
        
        # Validate request
        if not data or 'url' not in data:
            return Response(
                json.dumps({"error": "URL is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        # Get submission ID from URL
        submission_id = get_submission_id(data['url'])
        if not submission_id:
            return Response(
                json.dumps({"error": "Invalid Reddit URL"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        try:
            # Get submission from Reddit API
            submission = reddit.submission(id=submission_id)
            
            # Return post info
            return Response(
                json.dumps({
                    "title": submission.title,
                    "numComments": submission.num_comments
                }),
                status_code=200,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            return Response(
                json.dumps({"error": str(e)}),
                status_code=500,
                headers={"Content-Type": "application/json"}
            )
    except Exception as e:
        return Response(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        ) 