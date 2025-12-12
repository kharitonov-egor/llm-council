import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, model]) => {
    const modelShortName = model.split('/')[1] || model;
    result = result.replace(new RegExp(label, 'g'), `**${modelShortName}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings, pendingModels = [], isLoading = false }) {
  const [activeTab, setActiveTab] = useState(0);

  // Ensure activeTab is always valid when rankings change
  useEffect(() => {
    if (rankings.length === 0) {
      setActiveTab(0);
    } else if (activeTab >= rankings.length) {
      setActiveTab(rankings.length - 1);
    }
  }, [rankings.length, activeTab]);

  // Show nothing if no rankings and no pending models
  if ((!rankings || rankings.length === 0) && pendingModels.length === 0) {
    return null;
  }

  // Helper to get short model name
  const getShortName = (model) => model.split('/')[1] || model;

  // Get the current ranking safely
  const safeActiveTab = Math.min(activeTab, Math.max(0, rankings.length - 1));
  const currentRanking = rankings[safeActiveTab];

  return (
    <div className="stage stage2">
      <h3 className="stage-title">
        Stage 2: Peer Rankings
        {isLoading && pendingModels.length > 0 && (
          <span className="responses-count">
            {' '}({rankings.length}/{rankings.length + pendingModels.length})
          </span>
        )}
      </h3>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {/* Completed rankings */}
        {rankings.map((rank, index) => (
          <button
            key={`${rank.model}-${index}`}
            className={`tab ${safeActiveTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {getShortName(rank.model)}
          </button>
        ))}
        {/* Pending models */}
        {pendingModels.map((model) => (
          <button
            key={`pending-${model}`}
            className="tab pending"
            disabled
          >
            <span className="tab-spinner"></span>
            {getShortName(model)}
          </button>
        ))}
      </div>

      {currentRanking && (
        <div className="tab-content">
          <div className="ranking-model">
            {currentRanking.model}
          </div>
          <div className="ranking-content markdown-content">
            <ReactMarkdown>
              {deAnonymizeText(currentRanking.ranking, labelToModel)}
            </ReactMarkdown>
          </div>

          {currentRanking.parsed_ranking &&
           currentRanking.parsed_ranking.length > 0 && (
            <div className="parsed-ranking">
              <strong>Extracted Ranking:</strong>
              <ol>
                {currentRanking.parsed_ranking.map((label, i) => (
                  <li key={i}>
                    {labelToModel && labelToModel[label]
                      ? labelToModel[label].split('/')[1] || labelToModel[label]
                      : label}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  {agg.model.split('/')[1] || agg.model}
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
