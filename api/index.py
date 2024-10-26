from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import math
from collections import Counter, defaultdict
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import os
import logging
import random
import time
import praw
from dotenv import load_dotenv

# from tqdm import tqdm
# import spacy
# from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
# import numpy as np
# import traceback

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
nltk.data.path.append(os.path.join(BASE_DIR, 'nltk_data'))

# nltk_data_dir = os.path.join(ROOT_DIR, '.venv', 'nltk_data')
# os.makedirs(nltk_data_dir, exist_ok=True)
# nltk.data.path.append(nltk_data_dir)
# # nltk.download('punkt', download_dir=nltk_data_dir, quiet=True)
# nltk.download('punkt_tab', download_dir=nltk_data_dir, quiet=True)
# nltk.download('stopwords', download_dir=nltk_data_dir, quiet=True)

# stop_words = set(stopwords.words('english'))

# nlp = spacy.load('en_core_web_sm')

# spacy_stop_words = nlp.Defaults.stop_words
# custom_stop_words = spacy_stop_words.union(ENGLISH_STOP_WORDS).union(set(stopwords.words('english')))
# custom_stop_words = set(stopwords.words('english')).union(ENGLISH_STOP_WORDS)
custom_stop_words = set(stopwords.words('english'))

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.2365.66'
]

reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent="ReddiGist/1.0"
)

def get_reddit_data(url, retries=3):
    """Get Reddit data using official API"""
    try:
        submission_id = url.split('/comments/')[1].split('/')[0]
        
        submission = reddit.submission(id=submission_id)
        submission.comments.replace_more(limit=None)

        comments = []
        for comment in submission.comments.list():
            if hasattr(comment, 'body') and comment.author and comment.author.name != 'AutoModerator':
                comments.append({
                    'text': comment.body,
                    'score': comment.score
                })
        
        return {'comments': comments}

    except Exception as e:
        logger.error(f"Error fetching Reddit data: {str(e)}")
        return None

# Helper functions
def clean_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = ' '.join(text.split())
    return text

def extract_all_comments(data, comments):
    if isinstance(data, list):
        for item in data:
            extract_all_comments(item, comments)
    elif isinstance(data, dict):
        if 'body' in data and 'author' in data and data['author'] != 'AutoModerator':
            comments.append({
                'text': data['body'],
                'score': data.get('score', 0)
            })
        for value in data.values():
            extract_all_comments(value, comments)

def extract_common_phrases(comments, ngram_limit=5, min_occurrences=2):
    ngram_list = []
    
    for comment in comments:
        tokens = nltk.word_tokenize(comment['text'])
        
        for n in range(2, ngram_limit + 1):
            for ngram in nltk.ngrams(tokens, n):
                if not all(word.lower() in custom_stop_words for word in ngram):
                    ngram_list.append(ngram)
    
    ngram_counts = Counter(ngram_list)
    common_phrases = [ngram for ngram, count in ngram_counts.items() if count >= min_occurrences]
    
    return common_phrases

def tuple_to_string(phrase_tuple):
    return ' '.join(phrase_tuple)

def is_meaningful_phrase(phrase):
    capitalized_count = sum(1 for word in phrase if word[0].isupper())
    return capitalized_count >= 2

def remove_substrings(phrases):
    final_phrases = set()
    sorted_phrases = sorted(phrases, key=lambda x: len(x), reverse=True)
    
    for phrase in sorted_phrases:
        if not any(phrase.lower() in other.lower() for other in final_phrases):
            final_phrases.add(phrase)
    
    return final_phrases

def remove_grammar(phrases):
    grammar = {'a', 'an', 'the', 'i'}
    processed_phrases = []

    for phrase in phrases:
        words = phrase.split()

        if words and re.match(r'^\d+$', words[0]):
            words = words[1:]

        if words and words[0].lower() in grammar:
            words = words[1:]

        if words and words[-1].lower() in grammar:
            words = words[:-1]

        processed_phrases.append(' '.join(words))

    return processed_phrases

def remove_custom_words(phrase, custom_words):
    words = phrase.split()
    cleaned_words = [word for word in words if word.lower() not in custom_words]
    return ' '.join(cleaned_words)

def remove_common_only_phrases(phrases, custom_stop_words):
    filtered_phrases = []
    for phrase in phrases:
        words = phrase.split()
        if not all(word.lower() in custom_stop_words for word in words) and len(words) > 2:
            filtered_phrases.append(phrase)
    return filtered_phrases

def remove_all_lowercase_phrases(phrases):
    articles_and_common_words = {
        'A', 'An', 'The', 'And', 'But', 'Or', 'So', 'Because', 'However', 'If', 'In', 'On', 'At', 
        'For', 'By', 'To', 'From', 'With', 'About', 'Over', 'Under', 'Before', 'After', 
        'I', 'Ive', 'He', 'Hes', 'She', 'Shes', 'It', 'Its', 'They', 'Theyve', 'We', 'Weve', 'This', 'That', 'These', 'Those', 'Then', 
        'Now', 'Here', 'There', 'What', 'When', 'Where', 'Why', 'How', 'Who', 'Which'
    }
    
    filtered_phrases = []
    
    for phrase in phrases:
        words = phrase.split()
        capitalized_words = [word for word in words if word[0].isupper() and word not in articles_and_common_words]

        if capitalized_words:
            filtered_phrases.append(phrase)
    
    return filtered_phrases

def post_process_ngrams(phrases):
    phrases = [tuple_to_string(phrase) for phrase in phrases]
    processed_phrases = []
    seen_phrases = set()

    for phrase in phrases:
        phrase_lower = ' '.join(word.lower() for word in phrase.split())

        if phrase_lower not in seen_phrases:
            processed_phrases.append(phrase)
            seen_phrases.add(phrase_lower)

    final_phrases = set()
    for phrase in processed_phrases:
        phrase_str = phrase

        if is_meaningful_phrase(phrase_str.split()) or len(phrase_str.split()) > 2:
            final_phrases.add(phrase_str)

    return final_phrases

def combine_similar_phrases(phrases, similarity_threshold=3):
    combined_phrases = list(phrases)
    merged = True
    
    while merged:
        merged = False
        new_phrases = []
        skip = set()

        for i, phrase in enumerate(combined_phrases):
            if i in skip:
                continue

            phrase_words = phrase.split()
            combined_phrase = phrase

            for j, other_phrase in enumerate(combined_phrases):
                if i != j and j not in skip:
                    other_phrase_words = other_phrase.split()

                    if phrase_words[:similarity_threshold] == other_phrase_words[:similarity_threshold]:
                        combined_phrase = ' '.join(phrase_words + other_phrase_words[similarity_threshold:])
                        skip.add(j)
                        merged = True
                    elif phrase_words[-similarity_threshold:] == other_phrase_words[-similarity_threshold:]:
                        combined_phrase = ' '.join(phrase_words[:-similarity_threshold] + other_phrase_words)
                        skip.add(j)
                        merged = True
                    else:
                        combined_phrase = phrase

            new_phrases.append(combined_phrase)

        combined_phrases = new_phrases

    return set(combined_phrases)

def final_post_process(phrases, custom_words):
    phrases = remove_substrings(phrases)
    phrases = [remove_custom_words(phrase, custom_words) for phrase in phrases]
    phrases = combine_similar_phrases(phrases)
    phrases = remove_common_only_phrases(phrases, custom_stop_words)
    phrases = remove_grammar(phrases)
    
    return phrases

# def phrase_tfidf(phrases, comments, ngram_limit=5):
#     comment_texts = [comment['text'] for comment in comments]
    
#     vectorizer = TfidfVectorizer(vocabulary=phrases, ngram_range=(1, ngram_limit + 2), lowercase=False)
#     tfidf_matrix = vectorizer.fit_transform(comment_texts)

#     tfidf_scores = np.sum(tfidf_matrix.toarray(), axis=0)
#     phrase_tfidf_map = dict(zip(vectorizer.get_feature_names_out(), tfidf_scores))

#     return phrase_tfidf_map

# def calculate_tfidf(phrases, comments):
#     tf_scores = defaultdict(float)
#     df_scores = defaultdict(int)
#     N = len(comments)
    
#     for phrase in phrases:
#         phrase_lower = phrase.lower()
#         for comment in comments:
#             text_lower = comment['text'].lower()
#             count = text_lower.count(phrase_lower)
#             if count > 0:
#                 tf_scores[phrase] += 1 + math.log(count) if count > 0 else 0
#                 df_scores[phrase] += 1
    
#     tfidf_scores = {}
#     for phrase in phrases:
#         if df_scores[phrase] > 0:
#             tf = tf_scores[phrase]
#             idf = math.log((1 + N)/(1 + df_scores[phrase])) + 1
#             tfidf_scores[phrase] = tf * idf
    
#     norm = math.sqrt(sum(score * score for score in tfidf_scores.values()))
#     if norm > 0:
#         for phrase in tfidf_scores:
#             tfidf_scores[phrase] /= norm
    
#     return tfidf_scores

# def phrase_tfidf(phrases, comments):
#     return calculate_tfidf(phrases, comments)

# def compute_phrase_upvotes(phrases, comments):
#     phrase_upvote_map = defaultdict(int)

#     for comment in comments:
#         comment_text_lower = comment['text'].lower()

#         for phrase in phrases:
#             if phrase.lower() in comment_text_lower:
#                 phrase_upvote_map[phrase] += comment['score']

#     return phrase_upvote_map

def find_phrase_positions(comment_text, phrases):
    """
    Find sequential positions (1, 2, 3, ...) of phrases based on order of appearance
    regardless of their actual position in the text
    """
    positions = {}
    current_position = 1
    comment_lower = comment_text.lower()
    seen_phrases = set()
    
    for phrase in phrases:
        phrase_lower = phrase.lower()
        if phrase_lower in comment_lower and phrase_lower not in seen_phrases:
            positions[phrase] = current_position
            current_position += 1
            seen_phrases.add(phrase_lower)
    
    return positions

def calculate_phrase_score(upvotes, position, alpha=0.1):
    """Calculate score using the formula: Score = Upvotes / (Position^α)"""
    if position <= 0:
        return 0
    return upvotes / (position ** alpha)

def compute_phrase_scores(phrases, comments):
    """Compute scores for phrases based on sequential position and upvotes"""
    phrase_scores = defaultdict(float)
    
    for comment in comments:
        positions = find_phrase_positions(comment['text'], phrases)
        
        for phrase, position in positions.items():
            score = calculate_phrase_score(
                upvotes=max(1, comment['score']),
                position=position
            )
            phrase_scores[phrase] += score
    
    return phrase_scores

def top_phrases_combined(phrases, comments, top_n=10):
    """Get top phrases using position-based scoring"""
    phrase_scores = compute_phrase_scores(phrases, comments)
    
    sorted_phrases = sorted(
        phrase_scores.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    return sorted_phrases[:top_n]

@app.route('/api/top_phrases', methods=['POST'])
def get_top_reddit_phrases():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        urls = data.get('urls', [])
        if not urls:
            return jsonify({"error": "URLs are required"}), 400

        top_n = data.get('top_n', 3)
        custom_words_input = data.get('custom_words', '')
        custom_words = set(custom_words_input.lower().split(',')) if custom_words_input else set()
        ngram_limit = data.get('ngram_limit', 5)
        apply_remove_lowercase = data.get('apply_remove_lowercase', True)
        print_scores = data.get('print_scores', False)

        # Step 1: Fetch Reddit JSON for all URLs
        logger.info(f"Step (1/4): Fetching Reddit JSON data for {len(urls)} URLs...")
        all_comments = []

        for url in urls:
            try:
                reddit_data = get_reddit_data(url)
                if reddit_data and 'comments' in reddit_data:
                    all_comments.extend(reddit_data['comments'])
                else:
                    error_msg = f"Failed to fetch data from {url}"
                    logger.warning(error_msg)
                    return jsonify({"error": error_msg}), 503

            except Exception as e:
                error_msg = f"Error processing URL {url}: {str(e)}"
                logger.warning(error_msg)
                return jsonify({"error": error_msg}), 500

        if not all_comments:
            return jsonify({"error": "No comments found in the provided URLs"}), 404

        logger.info("Done.")

        # Step 2: Clean all comments
        logger.info("Step (2/4): Cleaning comments...")
        for comment in all_comments:
            comment['text'] = clean_text(comment['text'])
        logger.info(f"Total comments extracted: {len(all_comments)}")

        # Step 3: Extract Common Phrases
        logger.info("Step (3/4): Extracting common phrases...")
        min_occurrences = max(math.ceil(len(all_comments) / 40), 2)
        all_common_phrases = set()
        all_common_phrases_lower = set()

        while min_occurrences >= 2:
            common_phrases = extract_common_phrases(all_comments, ngram_limit=ngram_limit, min_occurrences=min_occurrences)
            common_phrases = post_process_ngrams(common_phrases)
            common_phrases = final_post_process(common_phrases, custom_words)

            if apply_remove_lowercase:
                common_phrases = remove_all_lowercase_phrases(common_phrases)
            
            print(common_phrases)

            new_phrases = set(phrase for phrase in common_phrases if phrase.lower() not in all_common_phrases_lower)
            all_common_phrases.update(new_phrases)
            all_common_phrases_lower.update(phrase.lower() for phrase in new_phrases)

            logger.info(f"Found {len(new_phrases)} unique phrases with min_occurrences={min_occurrences}. Total: {len(all_common_phrases)} phrases.")

            if len(all_common_phrases) >= top_n:
                break

            min_occurrences -= 1

        if not all_common_phrases:
            logger.warning("No common phrases found. Returning all unique words.")
            all_words = set()
            for comment in all_comments:
                all_words.update(comment['text'].split())
            all_common_phrases = list(all_words)[:top_n]

        # Step 4: Compute Top Phrases Using TF-IDF + Upvotes
        logger.info("Step (4/4): Calculating top phrases...")
        top_phrases = top_phrases_combined(all_common_phrases, all_comments, top_n=top_n)
        logger.info("Done.")

        result = []
        for idx, (phrase, score) in enumerate(top_phrases, 1):
            if print_scores:
                result.append(f'{phrase}: {score}')
            else:
                result.append(f'{phrase}')

        logger.info(f"Returning result: {result}")
        return jsonify({'top_phrases': result})

    except Exception as e:
        logger.error("An error occurred:", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
