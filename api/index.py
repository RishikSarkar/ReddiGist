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
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Tuple, List, Set

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

SUBMISSION_ID_REGEX = re.compile(r'/comments/([^/]+)/')
CLEAN_TEXT_REGEX = re.compile(r'[^a-zA-Z\s]')
MULTISPACE_REGEX = re.compile(r'\s+')

def get_submission_id(url):
    match = SUBMISSION_ID_REGEX.search(url)
    return match.group(1) if match else None

def get_reddit_data(url, max_comments=10000, timeout=300):
    """Get Reddit data using official API within free tier limits"""
    try:
        submission_id = get_submission_id(url)
        if not submission_id:
            logger.warning(f"Invalid URL: {url}")
            return None

        submission = reddit.submission(id=submission_id)
        total_comments = submission.num_comments

        if total_comments <= 500:
            submission.comments.replace_more(limit=None)
        else:
            submission.comments.replace_more(limit=32)

        comments = []
        comment_count = 0
        start_time = time.time()
        
        for comment in submission.comments.list():
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout reached for {url} after {comment_count} comments")
                break
                
            if comment_count >= max_comments:
                logger.warning(f"Max comments ({max_comments}) reached for {url}")
                break
                
            if hasattr(comment, 'body') and comment.author and comment.author.name != 'AutoModerator':
                comments.append({
                    'text': comment.body,
                    'score': comment.score
                })
                comment_count += 1
        
        if comments:
            logger.info(f"Successfully fetched {len(comments)} comments from {url}")
            return {'comments': comments}
        else:
            logger.warning(f"No comments fetched from {url}")
            return None

    except Exception as e:
        logger.error(f"Error fetching Reddit data: {str(e)}")
        return None

# Helper functions
@lru_cache(maxsize=1000)
def tokenize_and_filter(text: str) -> Tuple[str, ...]:
    """Cache tokenization results for identical text."""
    tokens = word_tokenize(text)
    return tuple(token for token in tokens)

@lru_cache(maxsize=100)
def clean_text_cached(text: str) -> str:
    """Cache text cleaning results."""
    text = CLEAN_TEXT_REGEX.sub('', text)
    return MULTISPACE_REGEX.sub(' ', text).strip()

def clean_text(text):
    return clean_text_cached(text)

def extract_common_phrases(comments, ngram_limit=5, min_occurrences=2):
    """Extract common n-grams from comments."""
    ngram_list = []
    
    for comment in comments:
        tokens = tokenize_and_filter(comment['text'])
        
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
    """Find sequential positions of phrases based on order of appearance"""
    positions = {}
    current_position = 1
    comment_lower = comment_text.lower()
    seen_phrases = set()
    remaining_phrases = len(phrases)
    
    for phrase in phrases:
        phrase_lower = phrase.lower()
        if phrase_lower in comment_lower and phrase_lower not in seen_phrases:
            positions[phrase] = current_position
            current_position += 1
            seen_phrases.add(phrase_lower)
            remaining_phrases -= 1
            
            if remaining_phrases == 0:
                break
    
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

def is_substring_of_any(phrase, other_phrases):
    """Check if phrase is a substring of any other phrase"""
    phrase_lower = phrase.lower()
    for other in other_phrases:
        if phrase_lower in other.lower() and phrase_lower != other.lower():
            return True
    return False

def is_incomplete_phrase(phrase):
    """Check if phrase ends with common connecting words"""
    connecting_words = {'and', 'or', 'of', 'the', 'in', 'on', 'at', 'to', 'for', 'with'}
    words = phrase.split()
    return (len(words) > 0 and words[-1].lower() in connecting_words)

def top_phrases_combined(phrases, comments, top_n=10):
    """Get top phrases using position-based scoring with substring deduplication"""
    phrase_scores = compute_phrase_scores(phrases, comments)
    
    sorted_phrases = sorted(
        phrase_scores.items(), 
        key=lambda x: x[1],
        reverse=True
    )
    
    final_phrases = []
    seen_phrases = set()
    
    for phrase, score in sorted_phrases:
        if (not is_incomplete_phrase(phrase) and
            phrase.lower() not in seen_phrases and 
            not is_substring_of_any(phrase, final_phrases)):
            
            final_phrases.append(phrase)
            seen_phrases.add(phrase.lower())
            
            if len(final_phrases) >= top_n:
                break
    
    if len(final_phrases) < top_n:
        remaining_needed = top_n - len(final_phrases)
        for phrase, score in sorted_phrases:
            if (phrase not in final_phrases and 
                not is_incomplete_phrase(phrase) and
                phrase.lower() not in seen_phrases):
                
                final_phrases.append(phrase)
                seen_phrases.add(phrase.lower())
                
                remaining_needed -= 1
                if remaining_needed <= 0:
                    break

    return [(phrase, phrase_scores[phrase]) for phrase in final_phrases[:top_n]]

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
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(get_reddit_data, url): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                reddit_data = future.result()
                if reddit_data and 'comments' in reddit_data:
                    all_comments.extend(reddit_data['comments'])
                else:
                    logger.warning(f"Failed to fetch data from {url}")

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
            
            clean_phrases = set()
            seen_phrases_lower = set()
            
            sorted_phrases = sorted(common_phrases, key=len, reverse=True)
            
            for phrase in sorted_phrases:
                if (not is_incomplete_phrase(phrase) and 
                    phrase.lower() not in seen_phrases_lower and
                    not is_substring_of_any(phrase, clean_phrases)):
                    
                    clean_phrases.add(phrase)
                    seen_phrases_lower.add(phrase.lower())
            
            new_phrases = set(phrase for phrase in clean_phrases 
                             if phrase.lower() not in all_common_phrases_lower)
            
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

        # Step 4: Compute Top Phrases Using position and upvote-based scoring
        logger.info("Step (4/4): Calculating top phrases...")
        top_phrases = top_phrases_combined(all_common_phrases, all_comments, top_n=top_n)
        logger.info("Done.")

        result = []
        for idx, (phrase, score) in enumerate(top_phrases, 1):
            if print_scores:
                result.append(f'{phrase}: {score}')
            else:
                result.append(f'{phrase}')

        response_data = {'top_phrases': result}

        if len(result) < top_n:
            response_data['warning'] = f"Only found {len(result)} relevant phrases. Add more threads if you'd like to see more!"

        logger.info(f"Returning result: {result}")
        return jsonify(response_data)

    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "socket" in error_msg.lower():
            error_msg = "Request timed out. Try reducing the number of threads or selecting threads with fewer comments."
        logger.error("An error occurred:", exc_info=True)
        return jsonify({"error": error_msg}), 500

if __name__ == '__main__':
    app.run(debug=True)
