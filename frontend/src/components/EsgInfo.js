import React, { useEffect, useState } from 'react';

function EsgInfo({ symbol, esgData: propEsgData }) {
  const [esgData, setEsgData] = useState(propEsgData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    console.log('EsgInfo props:', { symbol, propEsgData }); // Debug props
    if (propEsgData) {
      setEsgData(propEsgData);
      return;
    }

    if (!symbol) return;

    setLoading(true);
    setError('');
    setEsgData(null);

    fetch('http://localhost:8000/api/finnhub_esg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    })
      .then(res => res.json())
      .then(data => {
        console.log('Finnhub ESG response:', data); // Debug response
        if (data.error) {
          throw new Error(data.error);
        }
        setEsgData(data);
      })
      .catch(err => setError(`Failed to fetch ESG data: ${err.message}`))
      .finally(() => setLoading(false));
  }, [symbol, propEsgData]);

  if (loading) return <p>Loading ESG data...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;
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