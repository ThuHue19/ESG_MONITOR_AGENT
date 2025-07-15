// import React from 'react';

function ArticleList({ articles, onSelect }) {
  return (
    <div>
      <h2>Articles</h2>
      <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
        {articles.map((a, index) => (
          <li key={index} style={{ marginBottom: 10 }}>
            <button onClick={() => onSelect(a)} style={{ cursor: 'pointer', background: '#007bff', color: 'white', border: 'none', padding: '8px 12px', borderRadius: 4 }}>
              {a.title} ({a.company})
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ArticleList;
