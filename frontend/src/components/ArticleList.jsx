import React from 'react';

function ArticleList({ articles, onSelect }) {
  return (
    <div>
      <h2 style={{ color: '#0d47a1', fontFamily: 'Montserrat, sans-serif', fontSize: 24 }}>Articles</h2>
      <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
        {articles.map((a, index) => (
          <li key={index} style={{ marginBottom: 10 }}>
            <button
              onClick={() => onSelect(a)}
              style={{
                cursor: 'pointer',
                background: '#2196f3',
                color: 'white',
                border: 'none',
                padding: '8px 12px',
                borderRadius: 8,
                fontWeight: 'bold',
                transition: 'background-color 0.3s',
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#1976d2')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = '#2196f3')}
            >
              {a.title} ({a.company})
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ArticleList;
