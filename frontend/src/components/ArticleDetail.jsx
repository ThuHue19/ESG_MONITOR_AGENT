import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function ArticleDetail({ article, loading }) {
  return (
    <div
      style={{
        marginTop: 30,
        backgroundColor: '#e3f2fd',
        padding: 15,
        borderRadius: 10,
        border: '1px solid #90caf9',
        fontFamily: 'Montserrat, sans-serif',
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(13, 71, 161, 0.12)',
          padding: 20,
          borderRadius: 8,
          color: '#0d47a1',
          lineHeight: 1.6,
        }}
      >
        <h2>{article.title}</h2>
        <p><strong>Company:</strong> {article.company}</p>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: '#0d47a1',
            textDecoration: 'underline',
            display: 'inline-block',
            marginBottom: 15,
          }}
        >
          View Article
        </a>

        <h3>Analysis</h3>
        {loading ? (
          <p>Loading analysis...</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {article.analysis || 'No analysis available'}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}

export default ArticleDetail;
