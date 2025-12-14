import { useState, useEffect } from 'react';
import { api } from '../api';
import './Settings.css';

export default function Settings({ onClose }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [newModel, setNewModel] = useState('');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await api.getConfig();
      setConfig(data);
      setError(null);
    } catch (err) {
      setError(`Failed to load configuration: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);
      await api.updateConfig(config);
      setSuccess(true);
      // Keep success message visible longer since it has important info
      setTimeout(() => setSuccess(false), 8000);
    } catch (err) {
      setError(`Failed to save configuration: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAddModel = () => {
    if (newModel.trim() && !config.council_models.includes(newModel.trim())) {
      setConfig({
        ...config,
        council_models: [...config.council_models, newModel.trim()],
      });
      setNewModel('');
    }
  };

  const handleRemoveModel = (model) => {
    if (config.council_models.length > 1) {
      setConfig({
        ...config,
        council_models: config.council_models.filter((m) => m !== model),
        chairman_model: config.chairman_model === model 
          ? config.council_models[0] 
          : config.chairman_model,
      });
    } else {
      setError('At least one council model is required');
    }
  };

  const handleModelKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAddModel();
    }
  };

  if (loading) {
    return (
      <div className="settings-overlay">
        <div className="settings-panel">
          <div className="settings-loading">Loading configuration...</div>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="settings-overlay">
        <div className="settings-panel">
          <div className="settings-error">Failed to load configuration</div>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Council Configuration</h2>
          <button className="settings-close" onClick={onClose}>×</button>
        </div>

        <div className="settings-content">
          {error && (
            <div className="settings-message settings-error-message">
              {error}
            </div>
          )}
          {success && (
            <div className="settings-message settings-success-message">
              Configuration saved! Restart the backend server for changes to take effect.
            </div>
          )}

          <div className="settings-section">
            <label className="settings-label">Council Models</label>
            <p className="settings-description">
              Add or remove models that will participate in the council discussion.
            </p>
            <div className="settings-models-list">
              {config.council_models.map((model) => (
                <div key={model} className="settings-model-item">
                  <span className="settings-model-name">{model}</span>
                  <button
                    className="settings-remove-btn"
                    onClick={() => handleRemoveModel(model)}
                    disabled={config.council_models.length === 1}
                    title={
                      config.council_models.length === 1
                        ? 'At least one model is required'
                        : 'Remove model'
                    }
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            <div className="settings-add-model">
              <input
                type="text"
                className="settings-input"
                placeholder="e.g., openai/gpt-4o"
                value={newModel}
                onChange={(e) => setNewModel(e.target.value)}
                onKeyPress={handleModelKeyPress}
              />
              <button
                className="settings-add-btn"
                onClick={handleAddModel}
                disabled={!newModel.trim() || config.council_models.includes(newModel.trim())}
              >
                Add Model
              </button>
            </div>
          </div>

          <div className="settings-section">
            <label className="settings-label">Chairman Model</label>
            <p className="settings-description">
              The model that synthesizes the final response from all council members.
            </p>
            <select
              className="settings-select"
              value={config.chairman_model}
              onChange={(e) =>
                setConfig({ ...config, chairman_model: e.target.value })
              }
            >
              {config.council_models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>

          <div className="settings-section">
            <label className="settings-label">Default Reasoning Effort</label>
            <p className="settings-description">
              Default reasoning effort level for models that support it.
            </p>
            <select
              className="settings-select"
              value={config.default_reasoning_effort || 'none'}
              onChange={(e) =>
                setConfig({
                  ...config,
                  default_reasoning_effort:
                    e.target.value === 'none' ? null : e.target.value,
                })
              }
            >
              <option value="none">None (disabled)</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="settings-section">
            <label className="settings-label">Model-Specific Reasoning</label>
            <p className="settings-description">
              Advanced: Configure reasoning parameters for specific models. This requires editing the config file directly.
            </p>
            <div className="settings-info-box">
              <pre className="settings-code">
                {JSON.stringify(config.model_reasoning_config, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button
            className="settings-cancel-btn"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            className="settings-save-btn"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}
