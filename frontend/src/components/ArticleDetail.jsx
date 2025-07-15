// import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function ArticleDetail({ article, analysis, loading }) {
  return (
    <div style={{ marginTop: 20 }}>
      <h2>{article.title}</h2>
      <p><strong>Company:</strong> {article.company}</p>
      <a href={article.url} target="_blank" rel="noopener noreferrer">View Article</a>

      <h3>Analysis</h3>
      {loading ? (
        <p>Loading analysis...</p>
      ) : (
        <div
          style={{
            backgroundColor: '#f0f0f0',
            padding: 10,
            borderRadius: 5,
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {analysis || 'No analysis available'}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export default ArticleDetail;
