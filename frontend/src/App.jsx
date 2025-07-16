import React, { useState, useEffect, useRef } from 'react';
import ArticleList from './components/ArticleList';
import ArticleDetail from './components/ArticleDetail';
import ReactMarkdown from 'react-markdown';
import EsgInfo from './components/EsgInfo';

const API_BASE =
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
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

const App = () => {
  const [input, setInput] = useState('');
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [summaries, setSummaries] = useState({});
  const [esgData, setEsgData] = useState({});
  const [isQuestion, setIsQuestion] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    const saved = localStorage.getItem('searchHistory');
    if (saved) setHistory(JSON.parse(saved));
  }, []);

  const saveHistory = (term) => {
    setHistory((prev) => {
      const updated = [...new Set([term, ...prev])].slice(0, 5);
      localStorage.setItem('searchHistory', JSON.stringify(updated));
      return updated;
    });
  };

  const handleSpeech = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.onstart = () => {
      setIsRecording(true);
      setError('');
    };
    recognition.onresult = (event) => {
      setInput(event.results[0][0].transcript);
    };
    recognition.onerror = (event) => {
      console.error('Speech error:', event.error);
      setError('Speech recognition failed.');
      setIsRecording(false);
    };
    recognition.onend = () => setIsRecording(false);
    recognition.start();
  };

  const handleSearch = () => {
    if (!input.trim()) return;

    setLoading(true);
    setArticles([]);
    setSelectedArticle(null);
    setError('');
    setSummaries({});
    setEsgData({});
    setIsQuestion(false);

    const lower = input.toLowerCase();
    const isQ = lower.includes('which') || lower.includes('what') || lower.includes('in the');
    setIsQuestion(isQ);

    if (isQ) {
      fetch(`${API_BASE}/api/search_query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.error) {
            setError(data.error);
          } else {
            const company = data.company || input;
            setEsgData({ [company]: data });
            <div style={{ color: '#0d47a1', whiteSpace: 'pre-wrap' }}>
  {summary}
</div>



            fetch(`${API_BASE}/api/analyze_companies`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ companies: [company] }),
            })
              .then((res) => res.json())
              .then((arr) => {
                const all = [];
                arr.forEach((c) => {
                  c.articles.forEach((a) => all.push({ ...a, company: c.company }));
                });
                setArticles(all);
              })
              .catch(() => setError('Failed to fetch articles.'));
          }
          saveHistory(input);
        })
        .catch(() => setError('Error connecting to backend.'))
        .finally(() => setLoading(false));
    } else {
      const names = input.split(/,| and | & /i).map((n) => n.trim()).filter((n) => n.length > 0);
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
        .then((res) => res.json())
        .then((data) => {
          const all = [];
          const newSum = {};
          const newESG = {};

          data.forEach((c) => {
            c.articles.forEach((a) => all.push({ ...a, company: c.company }));
            newSum[c.company] = c.overall_summary;
            if (c.esg) newESG[c.company] = c.esg;
          });

          if (all.length === 0) setError('No articles found.');
          setArticles(all);
          setSummaries(newSum);
          setEsgData(newESG);
          saveHistory(input);
        })
        .catch(() => setError('Error connecting to backend.'))
        .finally(() => setLoading(false));
    }
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div style={{ maxWidth: 800, margin: 'auto', padding: 20, fontFamily: 'Montserrat, sans-serif' }}>
    <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20, alignItems: 'center' }}>
      <h1 style={{ color: '#0d47a1' }}>ESG News Monitor</h1>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <img
          src="https://www.nus.edu.sg/images/default-source/identity-images/NUS_logo_full-horizontal.jpg"
          alt="NUS Logo"
          style={{ height: 120 }} // chỉnh đều chiều cao về 60px
        />
        <img
          src="https://ohh12.hcmut.edu.vn/img/news/RQ6hG8A_M89fTWtFX8YYwNPJ.jpg"
          alt="HUS Logo"
          style={{ height: 72, borderRadius: 8 }}
        />
      </div>
    </header>


      <div style={{ marginBottom: 10, display: 'flex', gap: 10 }}>
      <input
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleInputKeyDown}
        placeholder="Enter company names or a query..."
        style={{
          padding: 10,
          width: '100%',
          borderRadius: 8,
          border: '1px solid #2196f3',
          outlineColor: '#1976d2',
          fontSize: 16,
          fontFamily: 'Montserrat, sans-serif',
          color: '#0d47a1', // <- thêm dòng này để chữ có màu xanh
        }}
      />

        <button
          onClick={handleSearch}
          style={{
            padding: '16px 20px',
            borderRadius: 20,
            backgroundColor: '#2196f3',
            border: 'none',
            color: 'white',
            fontWeight: 'bold',
            fontSize: 16,
            fontFamily: 'Montserrat, sans-serif',
            cursor: 'pointer',
            minWidth: 100,
            height: 70,
          }}
        >
          Search
        </button>
        <button
          onClick={handleSpeech}
          disabled={isRecording}
          style={{
            padding: '10px 20px',
            borderRadius: 20,
            backgroundColor: isRecording ? '#a0cfff' : '#64b5f6',
            border: 'none',
            color: 'white',
            fontWeight: 'bold',
            fontSize: 16,
            fontFamily: 'Montserrat, sans-serif',
            cursor: isRecording ? 'not-allowed' : 'pointer',
            minWidth: 100,
            height: 70,
            display: 'flex',
            flexDirection: 'row',  // <-- thay đổi này
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8, // khoảng cách giữa chữ và icon
          }}
        >
          <div style={{ fontSize: '20px', lineHeight: '0.5' }}>🎤</div>
          <div>Speak</div>
          
        </button>
      </div>

      {history.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <strong style={{ color: '#0d47a1', fontSize: 24 }}>Search History:</strong>
          <ul style={{ paddingLeft: 15 }}>
            {history.map((h, i) => (
              <li
                key={i}
style={{
        cursor: 'pointer',
        padding: 4,
        color: '#0d47a1',  // ✅ thêm dòng này để đổi màu
        fontSize: 16,
        fontFamily: 'Montserrat, sans-serif',
      }}                onClick={() => {
                  setInput(h);
                  handleSearch();
                }}
              >
                {h}
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && <p style={{ color: '#0d47a1' }}>Loading...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {Object.entries(summaries).length > 0 && (
  <div
    style={{
      marginTop: 20,
      backgroundColor: '#e3f2fd',  // lớp nền nhạt bên ngoài
      padding: 15,
      borderRadius: 8,
      border: '1px solid #90caf9',
    }}
  >
    <h2 style={{ color: '#0d47a1' }}>Company Summaries</h2>
    {Object.entries(summaries).map(([company, summary], idx) => (
      <div
        key={company}
        style={{
          marginBottom: 20,
          backgroundColor: 'rgba(13, 71, 161, 0.12)',  // lớp nền đậm hơn bên trong
          padding: 20,
          borderRadius: 8,
          color: '#0d47a1',
          lineHeight: 1.6,
        }}
      >
        <h3 style={{ color: '#0d47a1' }}>{company}</h3>
        <EsgInfo symbol={companyToTicker[company] || company} esgData={esgData[company]} />
        <h4 style={{ color: '#0d47a1' }}>Investment Recommendation</h4>
        <ReactMarkdown
          components={{
            p: ({ node, ...props }) => (
              <p style={{ color: '#0d47a1', marginBottom: 8 }} {...props} />
            ),
            strong: ({ node, ...props }) => <strong style={{ color: '#0d47a1' }} {...props} />,
            em: ({ node, ...props }) => <em style={{ color: '#0d47a1' }} {...props} />,
            li: ({ node, ...props }) => <li style={{ color: '#0d47a1' }} {...props} />,
            a: ({ node, ...props }) => <a style={{ color: '#0d47a1' }} {...props} />,
            code: ({ node, ...props }) => <code style={{ color: '#0d47a1' }} {...props} />,
            div: ({ node, ...props }) => <div style={{ color: '#0d47a1' }} {...props} />,
            span: ({ node, ...props }) => <span style={{ color: '#0d47a1' }} {...props} />,
          }}
        >
          {summary}
        </ReactMarkdown>
      </div>
    ))}
  </div>
)}



      <ArticleList articles={articles} onSelect={setSelectedArticle} />
      {selectedArticle && <ArticleDetail article={selectedArticle} analysis={analysis} />}

      <footer
        style={{
          marginTop: 40,
          paddingTop: 20,
          borderTop: '1px solid #90caf9',
          textAlign: 'center',
          color: '#0d47a1',
          fontSize: 14,
        }}
      >
        Developed by <strong>Nguyen Thi Thu Hue</strong> – VNU University of Science, 2025
      </footer>
    </div>
  );
};

export default App;
