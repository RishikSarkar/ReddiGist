<p align="center">
  <h3 align="center">ReddiGist: Reddit Thread Summarizer</h3>
</p>

<p align="center">An intelligent Reddit thread summarizer that extracts key phrases and topics using NLP techniques and upvote-weighted TF-IDF scoring.</p>

<br/>

## Introduction

ReddiGist is a hybrid Next.js + Python application that automatically extracts and ranks the most significant phrases from Reddit thread comments. It combines Natural Language Processing (NLP) techniques with Reddit's voting system to identify the most relevant and meaningful discussions within a thread.

## How It Works

The application follows a sophisticated pipeline to process Reddit comments and extract meaningful phrases:

### 1. Data Retrieval
- Fetches Reddit thread data using Reddit's JSON API
- Extracts comments recursively from the thread's comment tree
- Filters out AutoModerator comments and deleted/removed content
- Preserves comment scores (upvotes) for weighted ranking

### 2. Comment Preprocessing
- Cleans text while preserving original casing
- Removes special characters and excessive whitespace
- Maintains capitalization for proper noun identification
- Filters out non-alphabetic characters while keeping spaces

### 3. Phrase Extraction
- Generates n-grams (n=2 to 5) from preprocessed comments
- Filters out n-grams containing only stop words
- Requires minimum occurrence threshold (default: 2) for phrase consideration
- Preserves original casing for meaningful phrase identification
- Uses NLTK's word_tokenize for consistent tokenization

### 4. Phrase Post-processing
The system applies multiple filters to ensure quality phrases:
- Removes substring duplicates (e.g., removes "Landing on" if "Crash Landing on You" exists)
- Filters out custom words provided in the request
- Combines similar phrases based on common starts/ends
- Removes phrases with only lowercase words (optional via apply_remove_lowercase parameter)
- Removes grammatical artifacts
- Requires at least two capitalized words for phrase consideration

### 5. Phrase Ranking
Implements a hybrid scoring system combining:
- TF-IDF (Term Frequency-Inverse Document Frequency)
  - Treats each comment as a document
  - Calculates phrase importance across the thread
- Upvote Weighting
  - Incorporates comment scores into phrase significance
  - Gives higher weight to phrases from highly upvoted comments

## Technical Implementation

### Backend (Flask)
- **Language:** Python
- **Framework:** Flask
- **Key Libraries:**
  - NLTK: Natural Language Processing
  - scikit-learn: TF-IDF Vectorization
  - NumPy: Numerical computations
  - spaCy: Advanced text processing (optional)

### Frontend (Next.js)
- **Language:** TypeScript/JavaScript
- **Framework:** Next.js
- **Key Features:**
  - Real-time phrase extraction
  - Interactive results display
  - Reddit thread URL input

## Getting Started

### Prerequisites
1. Python 3.8 or higher
2. Node.js 14 or higher
3. npm or pnpm

### Installation

1. Clone the repository:
```bash
git clone https://github.com/RishikSarkar/ReddiGist.git
cd ReddiGist
```

2. Create and activate Python virtual environment:
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Unix/MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
npm install
```

4. Run the development servers:
```bash
# In one terminal (Frontend)
npm run next-dev

# In another terminal (Backend)
npm run flask-dev
```

The application will be available at:
- Frontend: [http://localhost:3000](http://localhost:3000)
- API: [http://127.0.0.1:5328](http://127.0.0.1:5328)

## API Endpoints

### POST `/api/top_phrases`
Extracts top phrases from a Reddit thread.

**Request Body:**
```json
{
  "url": "reddit_thread_url",
  "custom_words": "optional,comma,separated,words,to,filter",
  "top_n": 3,
  "ngram_limit": 5,
  "apply_remove_lowercase": true,
  "print_scores": false
}
```

**Parameters:**
- `url` (required): Reddit thread URL
- `custom_words` (optional): Comma-separated words to filter out
- `top_n` (optional): Number of top phrases to return (default: 3)
- `ngram_limit` (optional): Maximum n-gram length (default: 5)
- `apply_remove_lowercase` (optional): Whether to remove lowercase-only phrases (default: true)
- `print_scores` (optional): Whether to print scoring details (default: false)

**Response:**
```json
{
  "top_phrases": [
    ["Phrase One", 0.85],
    ["Phrase Two", 0.72],
    ...
  ]
}
```

## Learn More

To learn more about the technologies used:

- [Next.js Documentation](https://nextjs.org/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [NLTK Documentation](https://www.nltk.org/)
- [scikit-learn TF-IDF](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)
- [spaCy Documentation](https://spacy.io/api/doc)
