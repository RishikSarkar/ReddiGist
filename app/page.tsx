'use client';

import { useState } from 'react';

export default function Home() {
  const [url, setUrl] = useState('');
  const [topN, setTopN] = useState('3');
  const [customWords, setCustomWords] = useState('');
  const [ngramLimit, setNgramLimit] = useState('5');
  const [applyRemoveLowercase, setApplyRemoveLowercase] = useState(true);
  const [printScores, setPrintScores] = useState(false);
  const [result, setResult] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResult([]);

    try {
      const response = await fetch('/api/top_phrases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          top_n: parseInt(topN),
          custom_words: customWords,
          ngram_limit: parseInt(ngramLimit),
          apply_remove_lowercase: applyRemoveLowercase,
          print_scores: printScores,
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setResult(data.top_phrases);
    } catch (error) {
      console.error('Error:', error);
      setResult(['An error occurred while fetching the data.']);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-white text-black p-8">
      <h1 className="text-4xl font-bold mb-8">ReddiGist</h1>
      <form onSubmit={handleSubmit} className="space-y-4 max-w-xl">
        <div>
          <label htmlFor="url" className="block mb-2 font-semibold">
            Reddit URL
          </label>
          <input
            type="text"
            id="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded"
            placeholder="https://www.reddit.com/r/AskReddit/comments/example"
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="topN" className="block mb-2 font-semibold">
              Top N Phrases
            </label>
            <input
              type="number"
              id="topN"
              value={topN}
              onChange={(e) => setTopN(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded"
              min="1"
            />
          </div>
          <div>
            <label htmlFor="ngramLimit" className="block mb-2 font-semibold">
              N-gram Limit
            </label>
            <input
              type="number"
              id="ngramLimit"
              value={ngramLimit}
              onChange={(e) => setNgramLimit(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded"
              min="1"
            />
          </div>
        </div>
        <div>
          <label htmlFor="customWords" className="block mb-2 font-semibold">
            Custom Words to Exclude
          </label>
          <input
            type="text"
            id="customWords"
            value={customWords}
            onChange={(e) => setCustomWords(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded"
            placeholder="word1,word2,word3"
          />
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="applyRemoveLowercase"
            checked={applyRemoveLowercase}
            onChange={(e) => setApplyRemoveLowercase(e.target.checked)}
            className="form-checkbox"
          />
          <label htmlFor="applyRemoveLowercase">Remove Lowercase Phrases</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="printScores"
            checked={printScores}
            onChange={(e) => setPrintScores(e.target.checked)}
            className="form-checkbox"
          />
          <label htmlFor="printScores">Print Scores</label>
        </div>
        <button
          type="submit"
          className="bg-black text-white py-2 px-4 rounded hover:bg-gray-800 transition-colors"
          disabled={isLoading}
        >
          {isLoading ? 'Gisting...' : 'Gist'}
        </button>
      </form>
      {result.length > 0 && (
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-4">Top Phrases</h2>
          <ul className="list-decimal list-inside space-y-2">
            {result.map((phrase, index) => (
              <li key={index} className="text-lg">
                {phrase}
              </li>
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}
