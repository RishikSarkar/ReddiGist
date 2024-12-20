'use client';

import { useState, useEffect } from 'react';

interface RedditPost {
  url: string;
  title: string;
  numComments?: number;
  effectiveComments?: number;
}

interface PhraseResult {
  phrase: string;
  score?: string;
  upvotes?: number;
}

const MAX_THREADS = 5;
const MAX_TOTAL_COMMENTS = 5000;

const DEFAULT_TOP_N = '3';
const DEFAULT_NGRAM_LIMIT = '5';
const DEFAULT_REMOVE_LOWERCASE = true;
const DEFAULT_PRINT_SCORES = false;

interface TooltipContent {
  title: string;
  description: string;
}

const tooltips: Record<string, TooltipContent> = {
  urlInput: {
    title: "Adding Reddit URLs",
    description: "Add Reddit thread URLs to analyze their comments for common meaningful phrases.\n\nHint: If adding a thread would exceed 5,000 total comments, only the top comments will be analyzed to stay within API limits."
  },
  topN: {
    title: "Number of Results",
    description: "How many top phrases to show in the results.\n\nHint: Higher numbers may include less relevant phrases. Note that top 3 items from a top 10 list might differ from a top 3 list due to how phrases are scored."
  },
  ngramLimit: {
    title: "Max Words per Phrase",
    description: "Maximum number of words to include in each phrase. Higher limits can catch longer phrases but may take longer to process.\n\nHint: Use 1-2 for lists of names (e.g., characters, actors), and 5 for longer phrases (e.g., movie titles, quotes)."
  },
  customWords: {
    title: "Custom Words to Exclude",
    description: "Add comma-separated words to exclude from results. Useful for filtering out common phrases specific to the subreddit or topic.\n\nHint: If 'Netflix Original Series' keeps appearing but isn't relevant, adding 'Netflix' will remove all phrases containing that word."
  },
  removeLowercase: {
    title: "Remove Lowercase Phrases",
    description: "Only keep phrases where both first and last words are capitalized. Helps focus on names, titles, and proper nouns.\n\nHint: Turn off in threads with common phrases or inconsistent capitalization."
  },
  showStats: {
    title: "Show Statistics",
    description: "Display vote counts and relevance scores for each phrase.\n\nHint: Phrases score slightly higher when appearing early in comments, helping catch top 10 lists while valuing regular discussion."
  }
};

const InfoTooltip: React.FC<{ content: TooltipContent }> = ({ content }) => (
  <div className="group relative inline-block ml-2">
    <div className="text-gray-500 hover:text-gray-400 cursor-help text-xs">ⓘ</div>
    <div className="invisible group-hover:visible absolute z-10 w-64 p-4 mt-2 bg-[#272729] rounded-lg shadow-lg border border-[#333D42] text-sm -left-20">
      <h3 className="font-semibold mb-2 text-[#D93900]">{content.title}</h3>
      {content.description.split('\n\nHint: ').map((text, index) => (
        index === 0 ? (
          <p key="description" className="text-gray-300 mb-2">{text}</p>
        ) : (
          <p key="hint" className="text-gray-400 text-xs italic">Hint: {text}</p>
        )
      ))}
    </div>
  </div>
);

export default function Home() {
  const [currentUrl, setCurrentUrl] = useState('');
  const [selectedPosts, setSelectedPosts] = useState<RedditPost[]>(() => 
    loadFromLocalStorage('selectedPosts', [])
  );
  const [topN, setTopN] = useState(() => 
    loadFromLocalStorage('topN', DEFAULT_TOP_N)
  );
  const [customWords, setCustomWords] = useState(() => 
    loadFromLocalStorage('customWords', '')
  );
  const [ngramLimit, setNgramLimit] = useState(() => 
    loadFromLocalStorage('ngramLimit', DEFAULT_NGRAM_LIMIT)
  );
  const [applyRemoveLowercase, setApplyRemoveLowercase] = useState(() => 
    loadFromLocalStorage('removeLowercase', DEFAULT_REMOVE_LOWERCASE)
  );
  const [printScores, setPrintScores] = useState(() => 
    loadFromLocalStorage('printScores', DEFAULT_PRINT_SCORES)
  );
  const [result, setResult] = useState<PhraseResult[]>(() => 
    loadFromLocalStorage('result', [])
  );
  const [isLoading, setIsLoading] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);
  const [loadingDots, setLoadingDots] = useState(0);
  const [isLoadingPost, setIsLoadingPost] = useState(false);
  const [loadingPostDots, setLoadingPostDots] = useState(0);
  const [progress, setProgress] = useState(0);
  const [maxTime, setMaxTime] = useState(60);
  const [progressInterval, setProgressInterval] = useState<NodeJS.Timeout | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [duplicateUrlMessage, setDuplicateUrlMessage] = useState<string | null>(null);
  const [currentTopic, setCurrentTopic] = useState<string>(() => 
    loadFromLocalStorage('currentTopic', 'Phrase')
  );

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isLoading) {
      interval = setInterval(() => {
        setLoadingDots(prev => (prev + 1) % 4);
      }, 500);
    }

    if (isLoadingPost) {
      interval = setInterval(() => {
        setLoadingPostDots(prev => (prev + 1) % 4);
      }, 500);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLoading, isLoadingPost]);

  useEffect(() => {
    saveToLocalStorage('selectedPosts', selectedPosts);
  }, [selectedPosts]);

  useEffect(() => {
    saveToLocalStorage('topN', topN);
  }, [topN]);

  useEffect(() => {
    saveToLocalStorage('customWords', customWords);
  }, [customWords]);

  useEffect(() => {
    saveToLocalStorage('ngramLimit', ngramLimit);
  }, [ngramLimit]);

  useEffect(() => {
    saveToLocalStorage('removeLowercase', applyRemoveLowercase);
  }, [applyRemoveLowercase]);

  useEffect(() => {
    saveToLocalStorage('printScores', printScores);
  }, [printScores]);

  useEffect(() => {
    saveToLocalStorage('result', result);
  }, [result]);

  useEffect(() => {
    saveToLocalStorage('currentTopic', currentTopic);
  }, [currentTopic]);

  const extractTitleFromUrl = (url: string): string => {
    const parts = url.split('/');
    return parts[parts.length - 2] || 'Unknown Post';
  };

  const handleAddUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    const submittedUrl = currentUrl;
    
    if (submittedUrl) {
      if (selectedPosts.some(post => post.url === submittedUrl)) {
        setCurrentUrl('');
        setDuplicateUrlMessage('URL already added...');
        setTimeout(() => setDuplicateUrlMessage(null), 1000);
        return;
      }
      
      const currentTotalComments = selectedPosts.reduce((sum, post) => sum + (post.numComments || 0), 0);
      setIsLoadingPost(true);
      
      try {
        const response = await fetch('/api/post_info', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url: submittedUrl }),
        });

        if (!response.ok) {
          throw new Error('Failed to fetch post info');
        }

        const data = await response.json();
        
        if (currentTotalComments >= MAX_TOTAL_COMMENTS) {
          setIsLoadingPost(false);
          setLoadingPostDots(0);
          setCurrentUrl(submittedUrl);
          setErrorMessage(`Maximum comment limit (${MAX_TOTAL_COMMENTS.toLocaleString()}) already reached. Cannot add more threads.`);
          return;
        }

        const remainingSpace = MAX_TOTAL_COMMENTS - currentTotalComments;
        const effectiveComments = Math.min(data.numComments, remainingSpace);
        
        const newPost: RedditPost = {
          url: submittedUrl,
          title: data.title,
          numComments: data.numComments,
          effectiveComments: effectiveComments
        };

        if (currentTotalComments + data.numComments > MAX_TOTAL_COMMENTS) {
          const message = `This thread has ${data.numComments.toLocaleString()} comments. Only the top ${effectiveComments.toLocaleString()} comments will be analyzed to stay within the ${MAX_TOTAL_COMMENTS.toLocaleString()} comment limit.`;
          setErrorMessage(message);
        }

        setSelectedPosts([...selectedPosts, newPost]);
        setCurrentUrl('');
      } catch (error) {
        console.error('Error fetching post info:', error);
        const newPost: RedditPost = {
          url: submittedUrl,
          title: extractTitleFromUrl(submittedUrl)
        };
        setSelectedPosts([...selectedPosts, newPost]);
        setCurrentUrl('');
      } finally {
        setIsLoadingPost(false);
        setLoadingPostDots(0);
      }
    }
  };

  const handleRemovePost = (urlToRemove: string) => {
    setSelectedPosts(selectedPosts.filter(post => post.url !== urlToRemove));
  };

  const calculateMaxTime = (totalComments: number, topN: string, ngramLimit: string): number => {
    const maxPossibleTime = 60;
    const minTime = 15;
    const baseTime = Math.sqrt(totalComments / MAX_TOTAL_COMMENTS) * maxPossibleTime * 0.1;
    const nFactor = Math.log2(Math.max(1, parseInt(topN))) * 0.5;
    const ngramFactor = (parseInt(ngramLimit) / 10);
    
    const calculatedTime = baseTime * nFactor * ngramFactor;
    
    return Math.min(maxPossibleTime, Math.max(minTime, Math.ceil(calculatedTime)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (selectedPosts.length === 0) return;
    
    setIsLoading(true);
    setResult([]);
    setWarning(null);
    setProgress(0);
    setCurrentTopic('Phrase');
    
    const totalComments = selectedPosts.reduce((sum, post) => sum + (post.numComments || 0), 0);
    const calculatedMaxTime = calculateMaxTime(totalComments, topN, ngramLimit);
    setMaxTime(calculatedMaxTime);
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + (100 / (calculatedMaxTime * 10));
      });
    }, 100);
    
    setProgressInterval(interval);
    
    try {
      const response = await fetch('/api/top_phrases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: selectedPosts.map(post => post.url),
          titles: selectedPosts.map(post => post.title),
          top_n: parseInt(topN),
          custom_words: customWords,
          ngram_limit: parseInt(ngramLimit),
          apply_remove_lowercase: applyRemoveLowercase
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Network response was not ok');
      }

      setResult(data.phrases || []);
      setCurrentTopic(data.topic || 'Phrase');
      
      if (data.warning) {
        setWarning(data.warning);
      }
      
      setProgress(100);
    } catch (error) {
      console.error('Error:', error);
      setResult([]);
      setWarning(error instanceof Error ? error.message : 'An error occurred while fetching the data.');
    } finally {
      if (progressInterval) {
        clearInterval(progressInterval);
        setProgressInterval(null);
      }
      setIsLoading(false);
    }
  };

  const handleClearUrls = () => {
    setSelectedPosts([]);
  };

  const handleResetDefaults = () => {
    localStorage.clear();
    setTopN(DEFAULT_TOP_N);
    setNgramLimit(DEFAULT_NGRAM_LIMIT);
    setCustomWords('');
    setApplyRemoveLowercase(DEFAULT_REMOVE_LOWERCASE);
    setPrintScores(DEFAULT_PRINT_SCORES);
    setResult([]);
  };

  return (
    <main className="min-h-screen bg-[#0e1113] text-white p-8">
      {errorMessage && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-[#1A1A1B] p-6 rounded-lg max-w-md w-full mx-4 border border-[#333D42]">
            <h3 className="text-[#D93900] font-semibold mb-4">Notice</h3>
            <p className="text-gray-300 mb-6">{errorMessage}</p>
            <div className="flex justify-end">
              <button
                onClick={() => setErrorMessage(null)}
                className="bg-[#D93900] text-white px-4 py-2 rounded hover:bg-[#ff4500] transition-colors"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-[#D93900] text-center">ReddiGist</h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* URL Input Section */}
          <div className="bg-[#1A1A1B] p-6 rounded-lg">
            <label htmlFor="url" className="mb-2 flex items-center">
              <span className="font-semibold">Add Reddit URLs</span>
              <InfoTooltip content={tooltips.urlInput} />
              <span className="text-sm text-gray-400 ml-2">
                {isMounted ? (
                  `(${selectedPosts.reduce((sum, post) => sum + (post.effectiveComments || post.numComments || 0), 0).toLocaleString()} / ${MAX_TOTAL_COMMENTS.toLocaleString()} comments)`
                ) : (
                  `(0 / ${MAX_TOTAL_COMMENTS.toLocaleString()} comments)`
                )}
              </span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                id="url"
                value={
                  isLoadingPost 
                    ? `Retrieving thread information${'.'.repeat(loadingPostDots)}`
                    : duplicateUrlMessage
                    ? duplicateUrlMessage
                    : currentUrl
                }
                onChange={(e) => setCurrentUrl(e.target.value)}
                className={`flex-1 p-2 border border-[#333D42] rounded bg-[#272729] focus:border-[#D93900] focus:outline-none ${
                  isLoadingPost || duplicateUrlMessage ? 'text-gray-400' : 'text-white'
                }`}
                placeholder="https://www.reddit.com/r/AskReddit/comments/example"
                disabled={isLoadingPost || duplicateUrlMessage !== null}
              />
              <button
                type="button"
                onClick={handleAddUrl}
                className="bg-[#115BCA] text-white py-2 px-4 rounded hover:bg-[#1e6fdd] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isLoadingPost || !currentUrl}
              >
                Add
              </button>
            </div>
          </div>

          {/* Selected Posts Display */}
          {selectedPosts.length > 0 && isMounted && (
            <>
              <div className="flex flex-wrap gap-2 mt-2 justify-center">
                {selectedPosts.map((post) => (
                  <div
                    key={post.url}
                    className="flex items-center gap-2 bg-[#272729] px-3 py-1 rounded-full border border-[#333D42] hover:border-[#D93900] transition-colors"
                  >
                    <a 
                      href={post.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm hover:text-[#D93900] transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {post.title}
                      {post.numComments && (
                        <span className="text-gray-400 ml-1">
                          ({post.numComments.toLocaleString()} comments)
                        </span>
                      )}
                    </a>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        handleRemovePost(post.url);
                      }}
                      className="text-gray-400 hover:text-[#D93900] transition-colors ml-1"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex justify-center gap-2 mt-2">
                <button
                  type="button"
                  onClick={handleClearUrls}
                  className="text-sm text-gray-400 hover:text-[#D93900] transition-colors"
                >
                  Clear All
                </button>
              </div>
            </>
          )}

          {/* Settings Section */}
          <div className="bg-[#1A1A1B] p-6 rounded-lg space-y-4">

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div>
                  <label htmlFor="topN" className="mb-2 flex items-center">
                    <span className="font-semibold">Number of Results</span>
                    <InfoTooltip content={tooltips.topN} />
                  </label>
                </div>
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
                <label htmlFor="ngramLimit" className="mb-2 flex items-center">
                  <span className="font-semibold">Max Words per Phrase</span>
                  <InfoTooltip content={tooltips.ngramLimit} />
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
              <label htmlFor="customWords" className="mb-2 flex items-center">
                <span className="font-semibold">Custom Words to Exclude</span>
                <InfoTooltip content={tooltips.customWords} />
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
                <div className="flex items-center">
                  <span className="font-semibold">Remove Lowercase Phrases</span>
                  <InfoTooltip content={tooltips.removeLowercase} />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="printScores"
                  checked={printScores}
                  onChange={(e) => setPrintScores(e.target.checked)}
                  className="form-checkbox text-[#D93900]"
                />
                <div className="flex items-center">
                  <span className="font-semibold">Show Statistics</span>
                  <InfoTooltip content={tooltips.showStats} />
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleResetDefaults}
                className="text-sm text-gray-400 hover:text-[#D93900] transition-colors"
              >
                Reset to Defaults
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="w-full bg-[#D93900] text-white py-3 px-4 rounded-lg hover:bg-[#ff4500] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading || (!isMounted ? true : selectedPosts.length === 0)}
          >
            {isLoading ? `Gisting${'.'.repeat(loadingDots)}` : 'Gist'}
          </button>

          {/* Progress Bar */}
          {isLoading && (
            <div className="mt-4">
              <div className="w-full bg-[#272729] rounded-full h-2.5 mb-1">
                <div 
                  className="bg-[#D93900] h-2.5 rounded-full transition-all duration-300 ease-linear"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="text-xs text-gray-400 text-right">
                {Math.round(progress)}%
              </div>
            </div>
          )}
        </form>

        {/* Results Section */}
        {Array.isArray(result) && result.length > 0 && (
          <div className="mt-8 bg-[#1A1A1B] p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4 text-[#D93900] text-center">
              Top {currentTopic}s
            </h2>
            {warning && (
              <div className="mb-4 p-3 bg-[#272729] rounded text-gray-400 text-sm">
                {warning}
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#333D42]">
                    <th className="py-2 px-4 text-left w-16 text-gray-400">#</th>
                    <th className="py-2 px-4 text-left text-gray-400">Phrase</th>
                    {printScores && (
                      <>
                        <th className="py-2 px-4 text-right text-gray-400">Votes</th>
                        <th className="py-2 px-4 text-right text-gray-400">Score</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {result.map((item, index) => (
                    <tr 
                      key={index}
                      className="border-b border-[#333D42] last:border-0 hover:bg-[#272729] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-400">{index + 1}</td>
                      <td className="py-3 px-4">{item.phrase}</td>
                      {printScores && (
                        <>
                          <td className="py-3 px-4 text-right text-gray-400">{item.upvotes}</td>
                          <td className="py-3 px-4 text-right text-gray-400">{item.score}</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

const saveToLocalStorage = (key: string, value: any) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(key, JSON.stringify(value));
  }
};

const loadFromLocalStorage = (key: string, defaultValue: any) => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : defaultValue;
  }
  return defaultValue;
};
