from flask import Flask, Response, request
import os
import json
import nltk

app = Flask(__name__)

@app.route('/api/top_phrases', methods=['POST'])
def api_top_phrases():
    try:
        data = json.loads(request.data)
        
        if not data or not data.get('urls') or not data.get('titles'):
            return Response(
                json.dumps({"error": "URLs and titles are required"}),
                status=400,
                mimetype='application/json'
            )

        result = [
            {"phrase": "Example Phrase 1", "score": "123.45", "upvotes": 100},
            {"phrase": "Example Phrase 2", "score": "67.89", "upvotes": 50}
        ]
        
        return Response(
            json.dumps({
                "phrases": result,
                "topic": "Example Topic",
                "warning": None
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