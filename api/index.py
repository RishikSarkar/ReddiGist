from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import math
from collections import Counter, defaultdict
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
import numpy as np
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import traceback
import os
import logging
import spacy

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

nltk_data_dir = os.path.join(ROOT_DIR, '.venv', 'nltk_data')
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)
nltk.download('punkt', download_dir=nltk_data_dir)
nltk.download('punkt_tab', download_dir=nltk_data_dir)
nltk.download('stopwords', download_dir=nltk_data_dir)

stop_words = set(stopwords.words('english'))

nlp = spacy.load('en_core_web_sm')

spacy_stop_words = nlp.Defaults.stop_words
custom_stop_words = spacy_stop_words.union(ENGLISH_STOP_WORDS).union(set(stopwords.words('english')))

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
                if not all(word.lower() in stop_words for word in ngram):
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

def remove_common_only_phrases(phrases, stop_words):
    filtered_phrases = []
    for phrase in phrases:
        words = phrase.split()
        if not all(word.lower() in stop_words for word in words) and len(words) > 2:
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
    phrases = remove_common_only_phrases(phrases, stop_words)
    phrases = remove_grammar(phrases)
    
    return phrases

def phrase_tfidf(phrases, comments, ngram_limit=5):
    comment_texts = [comment['text'] for comment in comments]
    
    vectorizer = TfidfVectorizer(vocabulary=phrases, ngram_range=(1, ngram_limit + 2), lowercase=False)
    tfidf_matrix = vectorizer.fit_transform(comment_texts)

    tfidf_scores = np.sum(tfidf_matrix.toarray(), axis=0)
    phrase_tfidf_map = dict(zip(vectorizer.get_feature_names_out(), tfidf_scores))

    return phrase_tfidf_map

def compute_phrase_upvotes(phrases, comments):
    phrase_upvote_map = defaultdict(int)

    for comment in comments:
        comment_text_lower = comment['text'].lower()

        for phrase in phrases:
            if phrase.lower() in comment_text_lower:
                phrase_upvote_map[phrase] += comment['score']

    return phrase_upvote_map

def top_phrases_combined(phrases, comments, top_n=10, ngram_limit=5):
    phrase_tfidf_map = phrase_tfidf(phrases, comments, ngram_limit)
    phrase_upvotes = compute_phrase_upvotes(phrases, comments)

    combined_scores = {}
    for phrase in phrases:
        combined_score = phrase_tfidf_map.get(phrase, 0) + phrase_upvotes.get(phrase, 0)
        combined_scores[phrase] = combined_score

    sorted_phrases = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_phrases[:top_n]

@app.route('/api/top_phrases', methods=['POST'])
def get_top_reddit_phrases():
    try:
        data = request.json
        if not data:
            logger.error("No JSON payload provided")
            return jsonify({"error": "No JSON payload provided"}), 400

        url = data.get('url')
        if not url:
            logger.error("URL is required")
            return jsonify({"error": "URL is required"}), 400

        top_n = data.get('top_n', 3)
        custom_words_input = data.get('custom_words', '')
        custom_words = set(custom_words_input.lower().split(',')) if custom_words_input else set()
        ngram_limit = data.get('ngram_limit', 5)
        apply_remove_lowercase = data.get('apply_remove_lowercase', True)
        print_scores = data.get('print_scores', False)

        # Step 1: Fetch Reddit JSON
        logger.info("Step (1/4): Fetching Reddit JSON data...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url + '.json', headers=headers)

        if response.status_code != 200:
            logger.error(f"Failed to fetch data from Reddit. Status code: {response.status_code}")
            return jsonify({"error": f'Failed to fetch data from Reddit. Status code: {response.status_code}'}), 500

        reddit_data = response.json()
        logger.info("Done.")

        # Step 2: Extract and Clean Comments
        logger.info("Step (2/4): Extracting and cleaning comments...")
        comments = []
        extract_all_comments(reddit_data, comments)

        for comment in tqdm(comments, desc="Cleaning comments"):
            comment['text'] = clean_text(comment['text'])
        logger.info(f"Total comments extracted: {len(comments)}")

        # Step 3: Extract Common Phrases
        logger.info("Step (3/4): Extracting common phrases...")
        min_occurrences = max(math.ceil(len(comments) / 40), 2)
        all_common_phrases = set()
        all_common_phrases_lower = set()

        while min_occurrences >= 2:
            common_phrases = extract_common_phrases(comments, ngram_limit=ngram_limit, min_occurrences=min_occurrences)
            common_phrases = post_process_ngrams(common_phrases)
            print(common_phrases)
            common_phrases = final_post_process(common_phrases, custom_words)
            print(common_phrases)

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
            for comment in comments:
                all_words.update(comment['text'].split())
            all_common_phrases = list(all_words)[:top_n]

        # Step 4: Compute Top Phrases Using TF-IDF + Upvotes
        logger.info("Step (4/4): Calculating top phrases...")
        top_phrases = top_phrases_combined(all_common_phrases, comments, top_n=top_n, ngram_limit=ngram_limit)
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)