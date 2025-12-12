import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses, pendingModels = [], isLoading = false }) {
  const [activeTab, setActiveTab] = useState(0);

  // Ensure activeTab is always valid when responses change
  useEffect(() => {
    if (responses.length === 0) {
      setActiveTab(0);
    } else if (activeTab >= responses.length) {
      setActiveTab(responses.length - 1);
    }
  }, [responses.length, activeTab]);

  // Show nothing if no responses and no pending models
  if ((!responses || responses.length === 0) && pendingModels.length === 0) {
    return null;
  }

  // Helper to get short model name
  const getShortName = (model) => model.split('/')[1] || model;

  // Get the current response safely
  const safeActiveTab = Math.min(activeTab, Math.max(0, responses.length - 1));
  const currentResponse = responses[safeActiveTab];

  return (
    <div className="stage stage1">
      <h3 className="stage-title">
        Stage 1: Individual Responses
        {isLoading && pendingModels.length > 0 && (
          <span className="responses-count">
            {' '}({responses.length}/{responses.length + pendingModels.length})
          </span>
        )}
      </h3>

      <div className="tabs">
        {/* Completed responses */}
        {responses.map((resp, index) => (
          <button
            key={`${resp.model}-${index}`}
            className={`tab ${safeActiveTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {getShortName(resp.model)}
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

      {currentResponse && (
        <div className="tab-content">
          <div className="model-name">{currentResponse.model}</div>
          <div className="response-text markdown-content">
            <ReactMarkdown>{currentResponse.response}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
