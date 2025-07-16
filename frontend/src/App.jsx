import React, { useState, useEffect } from 'react';
import ArticleList from './components/ArticleList';
import ArticleDetail from './components/ArticleDetail';
import ReactMarkdown from 'react-markdown';
import EsgInfo from './components/EsgInfo';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://esg-monitor-agent.onrender.com';


const companyToTicker = {
  Tesla: 'TSLA',
  'First Solar': 'FSLR',
  'Brookfield Renewable': 'BEP',
  'NextEra Energy': 'NEE',
  Vestas: 'VWS',
  Orsted: 'ORSTED.CO',
  'Enphase Energy': 'ENPH',
  'ATA Creativity Global': 'AACG',
};

const companyList = Object.keys(companyToTicker);

function App() {
  const [input, setInput] = useState('');
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [summaries, setSummaries] = useState({});
  const [suggestedCompanies, setSuggestedCompanies] = useState([]);
  const [esgData, setEsgData] = useState({});
  const [isQuestion, setIsQuestion] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('searchHistory');
    if (saved) setHistory(JSON.parse(saved));
  }, []);

  const saveHistory = (term) => {
    const updated = [...new Set([term, ...history])].slice(0, 5);
    setHistory(updated);
    localStorage.setItem('searchHistory', JSON.stringify(updated));
  };

  const handleSpeech = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.start();
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
    };
    recognition.onerror = (event) => {
      console.error('Speech error:', event.error);
      setError('Speech recognition failed.');
    };
  };

  const handleSearch = () => {
    if (!input.trim()) return;

    setLoading(true);
    setArticles([]);
    setSelectedArticle(null);
    setError('');
    setSummaries({});
    setSuggestedCompanies([]);
    setEsgData({});
    setIsQuestion(false);

    const lowerInput = input.toLowerCase();
    const questionCheck = lowerInput.includes('which') || lowerInput.includes('what') || lowerInput.includes('in the');
    setIsQuestion(questionCheck);

    if (questionCheck) {
      fetch(`${API_BASE}/api/search_query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
      })
        .then(res => res.json())
        .then(data => {
          if (data.error) {
            setError(data.error);
          } else {
            const company = data.company || input;
            setEsgData({ [company]: data });
            setSummaries({
              [company]: `ESG Scores: Environmental ${data.environment_score ?? 'N/A'}, Social ${data.social_score ?? 'N/A'}, Governance ${data.governance_score ?? 'N/A'}, Total ${data.total_score ?? 'N/A'}`,
            });
            fetch(`${API_BASE}/api/analyze_companies`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ companies: [company] }),
            })
              .then(res => res.json())
              .then(companyData => {
                const allArticles = [];
                companyData.forEach(c => {
                  c.articles.forEach(article => {
                    allArticles.push({ ...article, company: c.company });
                  });
                });
                setArticles(allArticles);
              })
              .catch(() => setError('Failed to fetch articles.'));
          }
          saveHistory(input);
        })
        .catch(() => {
          setError('Error connecting to backend.');
        })
        .finally(() => setLoading(false));
    } else {
      const names = input
        .split(/,| and | & /i)
        .map(n => n.trim())
        .filter(n => n.length > 0);

      if (names.length === 0) {
        setError('Please enter valid company names or a query.');
        setLoading(false);
        return;
      }

      fetch(`${API_BASE}/api/analyze_companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companies: names }),
      })
        .then(res => res.json())
        .then(data => {
          const allArticles = [];
          const newSummaries = {};
          const newEsgData = {};

          data.forEach(companyData => {
            companyData.articles.forEach(article => {
              allArticles.push({ ...article, company: companyData.company });
            });
            newSummaries[companyData.company] = companyData.overall_summary;

            const ticker = companyToTicker[companyData.company] || companyData.company;
            fetch(`${API_BASE}/api/finnhub_esg`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ symbol: ticker }),
            })
              .then(res => res.json())
              .then(esg => {
                if (!esg.error) {
                  newEsgData[companyData.company] = esg;
                  setEsgData(prev => ({ ...prev, [companyData.company]: esg }));
                }
              })
              .catch(() => console.error(`Failed to fetch ESG for ${companyData.company}`));
          });

          if (allArticles.length === 0) {
            setError('No articles found.');
          }

          setArticles(allArticles);
          setSummaries(newSummaries);
          saveHistory(input);
        })
        .catch(() => {
          setError('Error connecting to backend.');
        })
        .finally(() => setLoading(false));
    }
  };

  const handleSelectArticle = (article) => {
    setSelectedArticle(article);
    setAnalysis(article.analysis || 'No analysis available');
  };

  return (
    <div style={{ maxWidth: 800, margin: 'auto', padding: 20 }}>
      <h1>ESG News Monitor</h1>

      <div style={{ marginBottom: 10 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch();
          }}
          placeholder="Enter company names or a query (e.g., Which is the ESG score of ATA Creativity Global?)"
          style={{ padding: 8, width: 400, marginRight: 10 }}
        />
        <button onClick={handleSearch} style={{ padding: 8 }}>Search</button>
        <button onClick={handleSpeech} style={{ padding: 8, marginLeft: 5 }}>🎤 Speak</button>
      </div>

      {input && !isQuestion && (
        <ul style={{ background: '#f9f9f9', listStyle: 'none', padding: 5, border: '1px solid #ccc', maxWidth: 400 }}>
          {companyList
            .filter(c => c.toLowerCase().includes(input.toLowerCase()) && !input.includes(c))
            .map((c, i) => (
              <li
                key={i}
                onClick={() => setInput(input ? input + ', ' + c : c)}
                style={{ cursor: 'pointer', padding: 5 }}
              >
                {c}
              </li>
            ))}
        </ul>
      )}

      {history.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <strong>Search History:</strong>
          <ul style={{ paddingLeft: 15 }}>
            {history.map((h, i) => (
              <li key={i} style={{ cursor: 'pointer' }} onClick={() => setInput(h)}>
                {h}
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {Object.entries(summaries).length > 0 && (
        <div style={{ marginTop: 20, background: '#f5f5f5', padding: 10, borderRadius: 5 }}>
          <h2>Company Summaries</h2>
          {Object.entries(summaries).map(([company, summary]) => (
            <div key={company} style={{ marginBottom: 20 }}>
              <h3>{company}</h3>
              <EsgInfo
  symbol={companyToTicker[company] || company}
  esgData={esgData[company]}
  apiBase={API_BASE}   // thêm prop apiBase
/>

              <h4>Investment Recommendation</h4>
              <ReactMarkdown>{summary}</ReactMarkdown>
            </div>
          ))}
        </div>
      )}

      <ArticleList articles={articles} onSelect={handleSelectArticle} />
      {selectedArticle && (
        <ArticleDetail article={selectedArticle} analysis={analysis} />
      )}
    </div>
  );
}

export default App;
