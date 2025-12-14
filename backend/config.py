"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Default council members - list of OpenRouter model identifiers
# These are used as fallback if config.json doesn't exist
_DEFAULT_COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "deepseek/deepseek-v3.2"
]

# Default chairman model - synthesizes final response
_DEFAULT_CHAIRMAN_MODEL = "openai/gpt-5.2"

# Default reasoning effort level for models that support it.
# Common values: "low", "medium", "high"
# Set to None to disable reasoning parameter
_DEFAULT_REASONING_EFFORT = "medium"

# Model-specific reasoning overrides
# Some models use different reasoning parameter names or values.
# Format: { "model_id": { "param_name": "reasoning_effort", "value": "high" } }
# Use None as value to disable reasoning for a specific model.
_DEFAULT_MODEL_REASONING_CONFIG = {
    # GPT 5.2 uses "xhigh" for extended reasoning
    "openai/gpt-5.2": {"param_name": "reasoning_effort", "value": "high"},
    # Claude uses extended thinking with budget_tokens
    # "anthropic/claude-opus-4.5": {"param_name": "thinking", "value": {"type": "enabled", "budget_tokens": 10000}},
    # Gemini uses thinking_config
    # "google/gemini-3-pro-preview": {"param_name": "thinking", "value": {"thinking_budget": 8000}},
}

# Load configuration from JSON file (with fallback to defaults)
try:
    from .config_manager import load_config
    _config = load_config()
    COUNCIL_MODELS = _config["council_models"]
    CHAIRMAN_MODEL = _config["chairman_model"]
    DEFAULT_REASONING_EFFORT = _config["default_reasoning_effort"]
    MODEL_REASONING_CONFIG = _config["model_reasoning_config"]
except Exception:
    # Fallback to defaults if config_manager fails
    COUNCIL_MODELS = _DEFAULT_COUNCIL_MODELS
    CHAIRMAN_MODEL = _DEFAULT_CHAIRMAN_MODEL
    DEFAULT_REASONING_EFFORT = _DEFAULT_REASONING_EFFORT
    MODEL_REASONING_CONFIG = _DEFAULT_MODEL_REASONING_CONFIG

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"


def get_reasoning_config(model: str) -> dict | None:
    """
    Get the reasoning configuration for a specific model.
    
    Args:
        model: The model identifier (e.g., "openai/gpt-5.2")
    
    Returns:
        Dict with 'param_name' and 'value' keys, or None if reasoning is disabled
    """
    # Check for model-specific override
    if model in MODEL_REASONING_CONFIG:
        config = MODEL_REASONING_CONFIG[model]
        if config is None or config.get("value") is None:
            return None
        return config
    
    # Use default if no override and default is set
    if DEFAULT_REASONING_EFFORT is not None:
        return {"param_name": "reasoning_effort", "value": DEFAULT_REASONING_EFFORT}
    
    return None