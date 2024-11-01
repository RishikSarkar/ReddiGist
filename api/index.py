import os
import re
import math
import time
import logging
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import praw
from dotenv import load_dotenv
import psutil

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
nltk.data.path.append(os.path.join(BASE_DIR, 'nltk_data'))

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
NUMERIC_START_REGEX = re.compile(r'^\d+')
CONNECTING_WORDS_REGEX = re.compile(r'\b(and|or|of|the|in|on|at|to|for|with)\b$', re.IGNORECASE)
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

MAX_TOTAL_COMMENTS = 5000
VERCEL_TIMEOUT = 60

COMMON_STARTERS = {
    'I', 'Im', "I'm", 'Ive', "I've", 'It', "It's", 'Its',
    'He', 'She', 'They', 'We', 'You',
    'Hes', "He's", 'Shes', "She's", 
    'Theyre', "They're", 'Were', "We're", 'Youre', "You're",
    'This', 'That', 'These', 'Those',
    'There', 'Here', 'What', 'When', 'Where', 'Why', 'How',
    'My', 'His', 'Her', 'Their', 'Our', 'Your'
}

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

        try:
            submission = reddit.submission(id=submission_id)
            submission.comment_sort = 'top'
        except Exception as e:
            if "Too Many Requests" in str(e):
                logger.warning("Rate limit hit, waiting 5 seconds...")
                time.sleep(5)
                submission = reddit.submission(id=submission_id)
                submission.comment_sort = 'top'
            else:
                raise

        total_comments = submission.num_comments

        if total_comments <= 500:
            submission.comments.replace_more(limit=None)
        else:
            replace_limit = min(16, max(8, total_comments // 500))
            submission.comments.replace_more(limit=replace_limit)

        comments = []
        comment_count = 0
        start_time = time.time()
        
        comment_batch = []
        BATCH_SIZE = 100

        low_score_streak = 0
        MAX_LOW_SCORE_STREAK = 5
        MIN_ACCEPTABLE_SCORE = 1
        
        for comment in submission.comments.list():
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout reached for {url} after {comment_count} comments")
                break
                
            if comment_count >= max_comments:
                logger.warning(f"Max comments ({max_comments}) reached for {url}")
                break

            if not hasattr(comment, 'score') or not hasattr(comment, 'body') or not comment.author:
                continue
                
            comment_score = comment.score

            if comment_score < MIN_ACCEPTABLE_SCORE:
                low_score_streak += 1
                if low_score_streak >= MAX_LOW_SCORE_STREAK:
                    logger.info(f"Breaking early after {comment_count} comments due to {MAX_LOW_SCORE_STREAK} consecutive low-scoring comments")
                    break
                continue
            else:
                low_score_streak = 0
                
            if (comment.author.name != 'AutoModerator' and comment_score >= 0):
                comment_batch.append({
                    'text': comment.body,
                    'score': comment_score
                })
                comment_count += 1
                
                if len(comment_batch) >= BATCH_SIZE:
                    comments.extend(comment_batch)
                    comment_batch = []
                    
                    time.sleep(0.1)
        
        if comment_batch:
            comments.extend(comment_batch)
                
        if comments:
            logger.info(f"Successfully fetched {len(comments)} comments from {url} in {time.time() - start_time:.2f}s")
            return {'comments': comments}
        else:
            logger.warning(f"No comments fetched from {url}")
            return None

    except Exception as e:
        logger.error(f"Error fetching Reddit data: {str(e)}")
        return None

@lru_cache(maxsize=1000)
def tokenize_and_filter(text: str) -> Tuple[str, ...]:
    """Cache tokenization results for identical text."""
    tokens = word_tokenize(text)
    return tuple(token for token in tokens)

def clean_text(text):
    """Clean text by removing URLs, non-letters, and extra spaces."""
    text = URL_REGEX.sub('', text)
    text = CLEAN_TEXT_REGEX.sub('', text)
    return MULTISPACE_REGEX.sub(' ', text).strip()

def preprocess_ngram(ngram: Tuple[str, ...], remove_lowercase: bool = True, custom_words: set = None) -> bool:
    """Preprocess and validate an n-gram tuple.
    
    Filtering criteria:
    1. If remove_lowercase is True:
       - Single words must be uppercase
       - Multi-word phrases must have both first and last words capitalized OR end with a number
    2. If remove_lowercase is False:
       - Check for incomplete phrases
    3. Always:
       - Remove phrases starting with numbers
       - Remove phrases containing any custom word
       - Remove phrases containing only stopwords
       - Remove single word 'I' and any single-letter words
       - Remove common sentence starters and pronouns
    """
    if len(ngram) == 1:
        word = ngram[0]
        if len(word) <= 1 or word in COMMON_STARTERS:
            return False
        return not remove_lowercase or word[0].isupper()
    
    if custom_words and any(word.lower() in custom_words for word in ngram):
        logger.debug(f"Excluded n-gram '{' '.join(ngram)}' due to presence of a custom word.")
        return False
        
    first_word, last_word = ngram[0], ngram[-1]

    if first_word in COMMON_STARTERS:
        return False
    
    if NUMERIC_START_REGEX.match(first_word):
        return False
    
    if all(word.lower() in custom_stop_words for word in ngram):
        return False
        
    if remove_lowercase:
        return (first_word[0].isupper() and 
                ((last_word[0].isupper() and last_word != 'I') or bool(NUMERIC_START_REGEX.match(last_word))))
            
    if CONNECTING_WORDS_REGEX.search(last_word):
        return False
        
    return True

def extract_filtered_phrases(comments, ngram_limit=5, top_n=10, apply_remove_lowercase=True, custom_words=None):
    """Extract all relevant phrases and then select the top_n phrases after filtering."""
    
    ngram_counts = Counter()
    phrase_original = {}
    
    for comment in comments:
        tokens = tokenize_and_filter(comment['text'])
        for n in range(1, ngram_limit + 1):
            for ngram in nltk.ngrams(tokens, n):
                if preprocess_ngram(ngram, apply_remove_lowercase, custom_words):
                    phrase = ' '.join(ngram) if len(ngram) > 1 else ngram[0]
                    phrase_lower = phrase.lower()
                    ngram_counts[phrase_lower] += 1
                    if phrase_lower not in phrase_original or phrase.istitle():
                        phrase_original[phrase_lower] = phrase
    
    sorted_phrases = sorted(ngram_counts.items(), key=lambda x: len(x[0].split()), reverse=True)
    
    min_occurrences = min(30, max(math.ceil(len(comments) / 40), 2))
    all_common_phrases = set()
    all_common_phrases_lower = set()
    
    while min_occurrences >= 2 and len(all_common_phrases) < top_n:
        filtered_phrases = []
        
        for phrase_lower, count in sorted_phrases:
            if count >= min_occurrences and phrase_lower not in all_common_phrases_lower:
                phrase = phrase_original[phrase_lower]
                if ' ' in phrase:
                    filtered_phrases.append(phrase)
        
        for phrase_lower, count in sorted_phrases:
            if count >= min_occurrences and phrase_lower not in all_common_phrases_lower:
                phrase = phrase_original[phrase_lower]
                if ' ' not in phrase:
                    if not any(phrase_lower in p.lower() for p in filtered_phrases) and \
                       not any(phrase_lower in p.lower() for p in all_common_phrases):
                        filtered_phrases.append(phrase)
        
        if not filtered_phrases:
            min_occurrences -= 1
            continue
        
        filtered_phrases_sorted = sorted(
            filtered_phrases,
            key=lambda phrase: ngram_counts[phrase.lower()],
            reverse=True
        )
        
        for phrase in filtered_phrases_sorted:
            phrase_lower = phrase.lower()
            
            phrases_to_remove = set()
            skip_current = False
            
            for existing in all_common_phrases:
                existing_lower = existing.lower()
                
                if existing_lower in phrase_lower or phrase_lower in existing_lower:
                    if len(phrase_lower.split()) > len(existing_lower.split()):
                        phrases_to_remove.add(existing)
                        all_common_phrases_lower.remove(existing_lower)
                    else:
                        skip_current = True
                        break
            
            if skip_current:
                continue
                
            all_common_phrases.difference_update(phrases_to_remove)
            
            if len(all_common_phrases) < top_n or phrases_to_remove:
                all_common_phrases.add(phrase)
                all_common_phrases_lower.add(phrase_lower)
        
        logger.info(f"Applied min_occurrences={min_occurrences}, found {len(filtered_phrases_sorted)} phrases.")

        min_occurrences -= 1

    if not all_common_phrases:
        logger.warning("No common phrases found. Returning all unique words.")
        all_words = set()
        for comment in comments:
            all_words.update(comment['text'].split())
        all_common_phrases = set(list(all_words)[:top_n])
    
    top_phrases = sorted(
        all_common_phrases,
        key=lambda phrase: ngram_counts[phrase.lower()],
        reverse=True
    )[:top_n]
    
    logger.info(f"Selected top {len(top_phrases)} phrases based on frequency.")
    
    return top_phrases

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
    """Calculate score using the formula: Score = Upvotes / (Position ^ alpha)"""
    if position <= 0:
        return 0
    return upvotes / (position ** alpha)

def compute_phrase_scores(phrases, comments):
    """Compute scores for phrases based on sequential position and upvotes"""
    phrase_scores = defaultdict(float)
    phrase_total_upvotes = defaultdict(int)
    
    for comment in comments:
        positions = find_phrase_positions(comment['text'], phrases)
        
        for phrase, position in positions.items():
            score = calculate_phrase_score(
                upvotes=max(1, comment['score']),
                position=position
            )
            phrase_scores[phrase] += score
            phrase_total_upvotes[phrase] += max(1, comment['score'])
    
    return phrase_scores, phrase_total_upvotes

def is_substring_of_any(phrase, other_phrases):
    """Check if phrase is a substring of any other phrase or contains any other phrase"""
    phrase_lower = phrase.lower()
    for other in other_phrases:
        other_lower = other.lower()
        if (phrase_lower in other_lower or other_lower in phrase_lower) and phrase_lower != other_lower:
            return True
    return False

def is_incomplete_phrase(phrase):
    """Check if phrase ends with connecting words using regex."""
    return bool(CONNECTING_WORDS_REGEX.search(phrase))

def top_phrases_combined(phrases, comments, top_n=10):
    """Get top phrases using position-based scoring with substring deduplication"""
    global phrases_found
    phrases_found = 0
    
    phrase_scores, total_upvotes = compute_phrase_scores(phrases, comments)
    
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
        for phrase, score in sorted_phrases:
            if (phrase not in final_phrases and 
                not is_incomplete_phrase(phrase) and
                phrase.lower() not in seen_phrases):
                
                final_phrases.append(phrase)
                seen_phrases.add(phrase.lower())
                
                if len(final_phrases) >= top_n:
                    break

    return [(phrase, phrase_scores[phrase], total_upvotes[phrase]) 
            for phrase in final_phrases[:top_n]]

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

@app.route('/api/top_phrases', methods=['POST'])
def get_top_reddit_phrases():
    try:
        total_start_time = time.time()
        memory_start = get_memory_usage()
        
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

        # Step 1: Fetch Reddit JSON
        fetch_start = time.time()
        logger.info(f"Step (1/4): Fetching Reddit JSON data for {len(urls)} URLs...")
        all_comments = []
        total_comments = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {executor.submit(get_reddit_data, url): url for url in urls}
            for future in as_completed(future_to_url):
                if time.time() - total_start_time > VERCEL_TIMEOUT:
                    logger.warning("Approaching Vercel timeout limit, processing with current comments")
                    break
                    
                url = future_to_url[future]
                try:
                    reddit_data = future.result(timeout=2)
                    if reddit_data and 'comments' in reddit_data:
                        new_comments = reddit_data['comments']
                        remaining_space = MAX_TOTAL_COMMENTS - total_comments
                        if remaining_space > 0:
                            new_comments = new_comments[:remaining_space]
                            all_comments.extend(new_comments)
                            total_comments += len(new_comments)
                        
                        if total_comments >= MAX_TOTAL_COMMENTS:
                            logger.warning(f"Reached maximum total comments limit ({MAX_TOTAL_COMMENTS})")
                            break
                except Exception as e:
                    logger.warning(f"Error processing {url}: {str(e)}")
                    continue
        
        fetch_time = time.time() - fetch_start
        logger.info(f"Step 1 - Fetch time: {fetch_time:.2f}s, Comments: {len(all_comments)}")

        if not all_comments:
            return jsonify({"error": "No comments found in the provided URLs"}), 404
            
        if len(all_comments) > MAX_TOTAL_COMMENTS:
            logger.warning(f"Truncating {len(all_comments)} comments to {MAX_TOTAL_COMMENTS}")
            all_comments.sort(key=lambda x: x['score'], reverse=True)
            all_comments = all_comments[:MAX_TOTAL_COMMENTS]

        logger.info(f"Total comments after truncation: {len(all_comments)}")

        logger.info("Done.")

        # Step 2: Clean Comments
        clean_start = time.time()
        logger.info("Step (2/4): Cleaning comments...")
        for comment in all_comments:
            comment['text'] = clean_text(comment['text'])
        clean_time = time.time() - clean_start
        logger.info(f"Step 2 - Clean time: {clean_time:.2f}s")

        # Step 3: Extract Common Phrases
        extract_start = time.time()
        logger.info("Step (3/4): Extracting common phrases...")
        
        all_common_phrases = extract_filtered_phrases(
            comments=all_comments,
            ngram_limit=ngram_limit,
            top_n=top_n,
            apply_remove_lowercase=apply_remove_lowercase,
            custom_words=custom_words
        )
        
        total_extract_time = time.time() - extract_start
        logger.info(f"Step 3 - Total extraction time: {total_extract_time:.2f}s")

        # Step 4: Score and Rank
        score_start = time.time()
        logger.info("Step (4/4): Calculating top phrases...")
        top_phrases = top_phrases_combined(all_common_phrases, all_comments, top_n=top_n)
        score_time = time.time() - score_start
        logger.info(f"Step 4 - Scoring time: {score_time:.2f}s")

        total_time = time.time() - total_start_time
        memory_used = get_memory_usage() - memory_start
        
        logger.info("\nPerformance Summary:")
        logger.info(f"Total time: {total_time:.2f}s")
        logger.info(f"  - Fetch: {fetch_time:.2f}s ({(fetch_time/total_time)*100:.1f}%)")
        logger.info(f"  - Clean: {clean_time:.2f}s ({(clean_time/total_time)*100:.1f}%)")
        logger.info(f"  - Extract: {total_extract_time:.2f}s ({(total_extract_time/total_time)*100:.1f}%)")
        logger.info(f"  - Score: {score_time:.2f}s ({(score_time/total_time)*100:.1f}%)")
        logger.info(f"Memory usage: {memory_used:.1f}MB")
        logger.info(f"Comments processed: {len(all_comments)}")

        result = []
        for idx, (phrase, score, upvotes) in enumerate(top_phrases, 1):
            result.append({
                'phrase': phrase,
                'score': f'{score:.2f}',
                'upvotes': upvotes
            })

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

@app.route('/api/post_info', methods=['POST'])
def get_post_info():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400

        submission_id = get_submission_id(data['url'])
        if not submission_id:
            return jsonify({"error": "Invalid Reddit URL"}), 400

        submission = reddit.submission(id=submission_id)
        
        return jsonify({
            "title": submission.title,
            "numComments": submission.num_comments
        })

    except Exception as e:
        logger.error(f"Error fetching post info: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    app.run(debug=True)


# def remove_substrings(phrases):
#     final_phrases = set()
#     sorted_phrases = sorted(phrases, key=lambda x: len(x), reverse=True)
    
#     for phrase in sorted_phrases:
#         if not any(phrase.lower() in other.lower() for other in final_phrases):
#             final_phrases.add(phrase)
    
#     return final_phrases

# def remove_grammar(phrases):
#     """Remove grammar-related words from phrases."""
#     grammar = {'a', 'an', 'the', 'i'}
#     processed_phrases = set()

#     for phrase in phrases:
#         words = phrase.split()

#         if words and NUMERIC_START_REGEX.match(words[0]):
#             words = words[1:]

#         if words and words[0].lower() in grammar:
#             words = words[1:]
#         if words and words[-1].lower() in grammar:
#             words = words[:-1]

#         if words:
#             processed_phrases.add(' '.join(words))

#     return processed_phrases

# def remove_custom_words(phrase, custom_words):
#     words = phrase.split()
#     cleaned_words = [word for word in words if word.lower() not in custom_words]
#     return ' '.join(cleaned_words)

# def remove_common_only_phrases(phrases, custom_stop_words):
#     filtered_phrases = []
#     for phrase in phrases:
#         words = phrase.split()
#         if not all(word.lower() in custom_stop_words for word in words) and len(words) > 2:
#             filtered_phrases.append(phrase)
#     return filtered_phrases

# def combine_similar_phrases(phrases, similarity_threshold=3):
#     combined_phrases = list(phrases)
#     merged = True
    
#     while merged:
#         merged = False
#         new_phrases = []
#         skip = set()

#         for i, phrase in enumerate(combined_phrases):
#             if i in skip:
#                 continue

#             phrase_words = phrase.split()
#             combined_phrase = phrase

#             for j, other_phrase in enumerate(combined_phrases):
#                 if i != j and j not in skip:
#                     other_phrase_words = other_phrase.split()

#                     if phrase_words[:similarity_threshold] == other_phrase_words[:similarity_threshold]:
#                         combined_phrase = ' '.join(phrase_words + other_phrase_words[similarity_threshold:])
#                         skip.add(j)
#                         merged = True
#                     elif phrase_words[-similarity_threshold:] == other_phrase_words[-similarity_threshold:]:
#                         combined_phrase = ' '.join(phrase_words[:-similarity_threshold] + other_phrase_words)
#                         skip.add(j)
#                         merged = True
#                     else:
#                         combined_phrase = phrase

#             new_phrases.append(combined_phrase)

#         combined_phrases = new_phrases

#     return set(combined_phrases)

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




# def extract_common_phrases(comments, ngram_limit=5, min_occurrences=2):
#     """Extract common n-grams from comments."""
#     ngram_list = []
    
#     for comment in comments:
#         tokens = tokenize_and_filter(comment['text'])
        
#         for n in range(2, ngram_limit + 1):
#             for ngram in nltk.ngrams(tokens, n):
#                 if not all(word.lower() in custom_stop_words for word in ngram):
#                     ngram_list.append(ngram)
    
#     ngram_counts = Counter(ngram_list)
#     common_phrases = [ngram for ngram, count in ngram_counts.items() if count >= min_occurrences]
    
#     return common_phrases

# def tuple_to_string(phrase_tuple):
#     return ' '.join(phrase_tuple)

# def is_meaningful_phrase(phrase):
#     capitalized_count = sum(1 for word in phrase if word[0].isupper())
#     return capitalized_count >= 2

# def remove_all_lowercase_phrases(phrases):
#     common_words = {
#         'A', 'An', 'The', 'And', 'But', 'Or', 'So', 'Because', 'However', 'If', 'In', 'On', 'At', 
#         'For', 'By', 'To', 'From', 'With', 'About', 'Over', 'Under', 'Before', 'After', 
#         'I', 'Ive', 'He', 'Hes', 'She', 'Shes', 'It', 'Its', 'They', 'Theyve', 'We', 'Weve', 'This', 'That', 'These', 'Those', 'Then', 
#         'Now', 'Here', 'There', 'What', 'When', 'Where', 'Why', 'How', 'Who', 'Which'
#     }
    
#     filtered_phrases = []
    
#     for phrase in phrases:
#         words = phrase.split()
#         capitalized_words = [word for word in words if word[0].isupper() and word not in common_words]

#         if capitalized_words:
#             filtered_phrases.append(phrase)
    
#     return filtered_phrases

# def post_process_ngrams(phrases):
#     phrases = [tuple_to_string(phrase) for phrase in phrases]
#     processed_phrases = []
#     seen_phrases = set()

#     for phrase in phrases:
#         phrase_lower = ' '.join(word.lower() for word in phrase.split())

#         if phrase_lower not in seen_phrases:
#             processed_phrases.append(phrase)
#             seen_phrases.add(phrase_lower)

#     final_phrases = set()
#     for phrase in processed_phrases:
#         phrase_str = phrase

#         if is_meaningful_phrase(phrase_str.split()) or len(phrase_str.split()) > 2:
#             final_phrases.add(phrase_str)

#     return final_phrases

# def process_phrases_in_single_pass(phrases, custom_words, custom_stop_words):
#     """Combine all filtering steps into a single efficient pass"""
#     processed_phrases = set()
#     seen_phrases_lower = set()
#     grammar_words = {'a', 'an', 'the', 'i'}
#     articles_and_common_words = {
#         'A', 'An', 'The', 'And', 'But', 'Or', 'So', 'Because', 'However', 'If', 'In', 'On', 'At', 
#         'For', 'By', 'To', 'From', 'With', 'About', 'Over', 'Under', 'Before', 'After', 
#         'I', 'Ive', 'He', 'Hes', 'She', 'Shes', 'It', 'Its', 'They', 'Theyve', 'We', 'Weve', 
#         'This', 'That', 'These', 'Those', 'Then', 'Now', 'Here', 'There', 'What', 'When', 
#         'Where', 'Why', 'How', 'Who', 'Which'
#     }
    
#     for phrase in sorted(phrases, key=len, reverse=True):
#         phrase_lower = phrase.lower()
        
#         if phrase_lower in seen_phrases_lower:
#             continue
            
#         words = phrase.split()
        
#         if (len(words) <= 2 or
#             any(word.lower() in custom_words for word in words) or
#             all(word.lower() in custom_stop_words for word in words) or
#             is_incomplete_phrase(phrase) or
#             any(phrase_lower in other.lower() for other in processed_phrases)):
#             continue
        
#         capitalized_words = [word for word in words if word[0].isupper() and word not in articles_and_common_words]
#         if len(capitalized_words) < 2:
#             continue
            
#         if words and NUMERIC_START_REGEX.match(words[0]):
#             words = words[1:]
#         if words and words[0].lower() in grammar_words:
#             words = words[1:]
#         if words and words[-1].lower() in grammar_words:
#             words = words[:-1]
            
#         if words and len(words) >= 2:
#             cleaned_phrase = ' '.join(words)
#             processed_phrases.add(cleaned_phrase)
#             seen_phrases_lower.add(cleaned_phrase.lower())
            
#     return processed_phrases

# def final_post_process(phrases, custom_words):
#     """Single pass processing for all phrases"""
#     string_phrases = [tuple_to_string(phrase) if isinstance(phrase, tuple) else phrase for phrase in phrases]
#     return process_phrases_in_single_pass(string_phrases, custom_words, custom_stop_words)


# extract_start = time.time()
# logger.info("Step (3/4): Extracting common phrases...")
# min_occurrences = min(
#     30,
#     max(math.ceil(len(all_comments) / 40), 2)
# )
# all_common_phrases = set()
# all_common_phrases_lower = set()

# while min_occurrences >= 2:
#     phrases_start = time.time()
#     common_phrases = extract_common_phrases(all_comments, ngram_limit=ngram_limit, min_occurrences=min_occurrences)
#     extract_time = time.time() - phrases_start
    
#     post_start = time.time()
#     common_phrases = post_process_ngrams(common_phrases)
#     common_phrases = final_post_process(common_phrases, custom_words)
#     if apply_remove_lowercase:
#         common_phrases = remove_all_lowercase_phrases(common_phrases)
#     post_time = time.time() - post_start
    
#     logger.info(f"  Iteration (min_occurrences={min_occurrences}):")
#     logger.info(f"    - Extract time: {extract_time:.2f}s")
#     logger.info(f"    - Post-process time: {post_time:.2f}s")
#     logger.info(f"    - Phrases found: {len(common_phrases)}")

#     clean_phrases = set()
#     seen_phrases_lower = set()
    
#     sorted_phrases = sorted(common_phrases, key=len, reverse=True)
    
#     for phrase in sorted_phrases:
#         if (not is_incomplete_phrase(phrase) and 
#             phrase.lower() not in seen_phrases_lower and
#             not any(phrase.lower() in existing.lower() for existing in clean_phrases)):
            
#             clean_phrases.add(phrase)
#             seen_phrases_lower.add(phrase.lower())
            
#             if len(clean_phrases) >= top_n:
#                 break

#     new_phrases = set(phrase for phrase in clean_phrases 
#                      if phrase.lower() not in all_common_phrases_lower)
    
#     all_common_phrases.update(new_phrases)
#     all_common_phrases_lower.update(phrase.lower() for phrase in new_phrases)

#     logger.info(f"Found {len(new_phrases)} unique phrases with min_occurrences={min_occurrences}. Total: {len(all_common_phrases)} phrases.")

#     if len(all_common_phrases) >= top_n:
#         break

#     min_occurrences -= 1

# if not all_common_phrases:
#     logger.warning("No common phrases found. Returning all unique words.")
#     all_words = set()
#     for comment in all_comments:
#         all_words.update(comment['text'].split())
#     all_common_phrases = list(all_words)[:top_n]

# total_extract_time = time.time() - extract_start
# logger.info(f"Step 3 - Total extraction time: {total_extract_time:.2f}s")



# def filter_words(phrases_with_counts: list, custom_words: set = None) -> set:
#     """
#     Filter phrases based on substring relationships and frequencies.
    
#     Rules:
#     1. Sort by number of words descending, then by frequency descending.
#     2. If current phrase is a substring of a kept phrase:
#        - Equal frequency: Keep the longer (kept) phrase.
#        - Lower frequency: Keep the longer (kept) phrase.
#        - Higher frequency: Keep the current phrase if multi-word; otherwise, keep the kept phrase.

#     Additionally:
#     - Exclude any phrase containing any custom word.

#     Args:
#         phrases_with_counts: List of tuples (phrase, count).
#         custom_words: Set of words to exclude from phrases.

#     Returns:
#         Filtered set of phrases.
#     """
#     phrase_count_map = {phrase.lower(): count for phrase, count in phrases_with_counts}
    
#     sorted_phrases = sorted(
#         phrases_with_counts,
#         key=lambda x: (len(x[0].split()), x[1]),
#         reverse=True
#     )
    
#     final_phrases = set()
#     kept_phrases = []
    
#     for current_phrase, current_count in sorted_phrases:
#         should_keep = True
#         current_phrase_lower = current_phrase.lower()
        
#         if custom_words and any(word in current_phrase_lower.split() for word in {cw.lower() for cw in custom_words}):
#             logger.debug(f"Excluded phrase '{current_phrase}' because it contains a custom word.")
#             continue
        
#         for kept_phrase in kept_phrases:
#             kept_phrase_lower = kept_phrase.lower()
#             if current_phrase_lower in kept_phrase_lower:
#                 kept_count = phrase_count_map.get(kept_phrase_lower, 0)
                
#                 if current_count > kept_count and len(current_phrase.split()) > 1:
#                     final_phrases.discard(kept_phrase)
#                     kept_phrases.remove(kept_phrase)
#                     final_phrases.add(current_phrase)
#                     kept_phrases.append(current_phrase)
#                     logger.debug(f"Replaced '{kept_phrase}' with '{current_phrase}' based on frequency.")
#                 else:
#                     should_keep = False
#                     logger.debug(f"Discarded '{current_phrase}' in favor of kept phrase '{kept_phrase}'.")
#                 break
        
#         if should_keep:
#             final_phrases.add(current_phrase)
#             kept_phrases.append(current_phrase)
#             logger.debug(f"Kept phrase '{current_phrase}'.")
    
#     return final_phrases