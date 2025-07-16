import React from 'react';

function EsgInfo({ symbol, esgData }) {
  if (!esgData) return null;

  return (
    <div style={{ backgroundColor: '#eef6ff', padding: 10, borderRadius: 5, marginTop: 10 }}>
      <h4>ESG Scores for {esgData.company || symbol}</h4>
      <ul>
        <li><strong>Environmental Score:</strong> {esgData.environment_score ?? 'N/A'}</li>
        <li><strong>Social Score:</strong> {esgData.social_score ?? 'N/A'}</li>
        <li><strong>Governance Score:</strong> {esgData.governance_score ?? 'N/A'}</li>
        <li><strong>Overall ESG Score:</strong> {esgData.total_score ?? 'N/A'}</li>
      </ul>
    </div>
  );
}

export default EsgInfo;
