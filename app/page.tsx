'use client';

import { useState } from 'react';

interface RedditPost {
  url: string;
  title: string;
}

const MAX_THREADS = 5;

export default function Home() {
  const [currentUrl, setCurrentUrl] = useState('');
  const [selectedPosts, setSelectedPosts] = useState<RedditPost[]>([]);
  const [topN, setTopN] = useState('3');
  const [customWords, setCustomWords] = useState('');
  const [ngramLimit, setNgramLimit] = useState('5');
  const [applyRemoveLowercase, setApplyRemoveLowercase] = useState(true);
  const [printScores, setPrintScores] = useState(false);
  const [result, setResult] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);

  const extractTitleFromUrl = (url: string): string => {
    const parts = url.split('/');
    return parts[parts.length - 2] || 'Unknown Post';
  };

  const handleAddUrl = (e: React.FormEvent) => {
    e.preventDefault();
    if (currentUrl && !selectedPosts.some(post => post.url === currentUrl)) {
      if (selectedPosts.length >= MAX_THREADS) {
        alert(`Maximum ${MAX_THREADS} threads allowed to prevent timeout issues.`);
        return;
      }
      const newPost: RedditPost = {
        url: currentUrl,
        title: extractTitleFromUrl(currentUrl)
      };
      setSelectedPosts([...selectedPosts, newPost]);
      setCurrentUrl('');
    }
  };

  const handleRemovePost = (urlToRemove: string) => {
    setSelectedPosts(selectedPosts.filter(post => post.url !== urlToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedPosts.length === 0) return;
    
    setIsLoading(true);
    setResult([]);
    setWarning(null);

    try {
        const response = await fetch('/api/top_phrases', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                urls: selectedPosts.map(post => post.url),
                top_n: parseInt(topN),
                custom_words: customWords,
                ngram_limit: parseInt(ngramLimit),
                apply_remove_lowercase: applyRemoveLowercase,
                print_scores: printScores,
            }),
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Network response was not ok');
        }

        setResult(data.top_phrases);
        if (data.warning) {
            setWarning(data.warning);
        }
    } catch (error) {
        console.error('Error:', error);
        setResult([error instanceof Error ? error.message : 'An error occurred while fetching the data.']);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#0e1113] text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-[#D93900] text-center">ReddiGist</h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* URL Input Section */}
          <div className="bg-[#1A1A1B] p-6 rounded-lg">
            <label htmlFor="url" className="block mb-2 font-semibold">
              Add Reddit URLs
              <span className="text-sm text-gray-400 ml-2">
                (Max {MAX_THREADS} threads)
              </span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                id="url"
                value={currentUrl}
                onChange={(e) => setCurrentUrl(e.target.value)}
                className="flex-1 p-2 border border-[#333D42] rounded bg-[#272729] text-white focus:border-[#D93900] focus:outline-none"
                placeholder="https://www.reddit.com/r/AskReddit/comments/example"
              />
              <button
                type="button"
                onClick={handleAddUrl}
                className="bg-[#115BCA] text-white py-2 px-4 rounded hover:bg-[#1e6fdd] transition-colors"
              >
                Add
              </button>
            </div>
          </div>

          {/* Selected Posts Display */}
          {selectedPosts.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2 justify-center">
              {selectedPosts.map((post) => (
                <div
                  key={post.url}
                  className="flex items-center gap-2 bg-[#272729] px-3 py-1 rounded-full border border-[#333D42]"
                >
                  <span className="text-sm">{post.title}</span>
                  <button
                    type="button"
                    onClick={() => handleRemovePost(post.url)}
                    className="text-gray-400 hover:text-[#D93900]"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Settings Section */}
          <div className="bg-[#1A1A1B] p-6 rounded-lg space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="topN" className="block mb-2 font-semibold">
                  Number of Results
                </label>
                <div className="relative flex">
                  <input
                    type="number"
                    id="topN"
                    value={topN}
                    onChange={(e) => setTopN(e.target.value)}
                    className="w-full p-2 border border-[#333D42] rounded bg-[#272729] text-white focus:border-[#D93900] focus:outline-none [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:m-0 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:m-0 [&::-webkit-inner-spin-button]:appearance-none"
                    min="1"
                  />
                  <div className="absolute right-0 h-full flex flex-col border-l border-[#333D42]">
                    <button
                      type="button"
                      onClick={() => setTopN(String(parseInt(topN) + 1))}
                      className="flex-1 px-2 py-0.25 text-gray-400 hover:text-[#D93900] hover:bg-[#1A1A1B] rounded-tr text-[10px]"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      onClick={() => setTopN(String(Math.max(1, parseInt(topN) - 1)))}
                      className="flex-1 px-2 py-0.25 text-gray-400 hover:text-[#D93900] hover:bg-[#1A1A1B] rounded-br text-[10px]"
                    >
                      ▼
                    </button>
                  </div>
                </div>
              </div>
              <div>
                <label htmlFor="ngramLimit" className="block mb-2 font-semibold">
                  Max Words per Phrase
                </label>
                <div className="relative flex">
                  <input
                    type="number"
                    id="ngramLimit"
                    value={ngramLimit}
                    onChange={(e) => setNgramLimit(e.target.value)}
                    className="w-full p-2 border border-[#333D42] rounded bg-[#272729] text-white focus:border-[#D93900] focus:outline-none [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:m-0 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:m-0 [&::-webkit-inner-spin-button]:appearance-none"
                    min="1"
                  />
                  <div className="absolute right-0 h-full flex flex-col border-l border-[#333D42]">
                    <button
                      type="button"
                      onClick={() => setNgramLimit(String(parseInt(ngramLimit) + 1))}
                      className="flex-1 px-2 py-0.25 text-gray-400 hover:text-[#D93900] hover:bg-[#1A1A1B] rounded-tr text-[10px]"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      onClick={() => setNgramLimit(String(Math.max(1, parseInt(ngramLimit) - 1)))}
                      className="flex-1 px-2 py-0.25 text-gray-400 hover:text-[#D93900] hover:bg-[#1A1A1B] rounded-br text-[10px]"
                    >
                      ▼
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="customWords" className="block mb-2 font-semibold">
                Custom Words to Exclude (Case-Insensitive)
              </label>
              <input
                type="text"
                id="customWords"
                value={customWords}
                onChange={(e) => setCustomWords(e.target.value)}
                className="w-full p-2 border border-[#333D42] rounded bg-[#272729] text-white focus:border-[#D93900] focus:outline-none"
                placeholder="word1,word2,word3"
              />
            </div>

            <div className="flex flex-col space-y-2">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="applyRemoveLowercase"
                  checked={applyRemoveLowercase}
                  onChange={(e) => setApplyRemoveLowercase(e.target.checked)}
                  className="form-checkbox text-[#D93900]"
                />
                <label htmlFor="applyRemoveLowercase">Remove Lowercase Phrases</label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="printScores"
                  checked={printScores}
                  onChange={(e) => setPrintScores(e.target.checked)}
                  className="form-checkbox text-[#D93900]"
                />
                <label htmlFor="printScores">Print Scores</label>
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="w-full bg-[#D93900] text-white py-3 px-4 rounded-lg hover:bg-[#ff4500] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading || selectedPosts.length === 0}
          >
            {isLoading ? 'Gisting...' : 'Gist'}
          </button>
        </form>

        {/* Results Section */}
        {result.length > 0 && (
          <div className="mt-8 bg-[#1A1A1B] p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4 text-[#D93900] text-center">Top Phrases</h2>
            {warning && (
              <div className="mb-4 p-3 bg-[#272729] rounded text-gray-400 text-sm">
                {warning}
              </div>
            )}
            <ul className="list-decimal list-inside space-y-2">
              {result.map((phrase, index) => (
                <li key={index} className="text-lg">
                  {phrase}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
