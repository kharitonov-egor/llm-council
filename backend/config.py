"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "moonshotai/kimi-k2-thinking"
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "openai/gpt-5.2"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# =============================================================================
# Reasoning Configuration
# =============================================================================
# Default reasoning effort level for models that support it.
# Common values: "low", "medium", "high"
# Set to None to disable reasoning parameter
DEFAULT_REASONING_EFFORT = "high"

# Model-specific reasoning overrides
# Some models use different reasoning parameter names or values.
# Format: { "model_id": { "param_name": "reasoning_effort", "value": "high" } }
# Use None as value to disable reasoning for a specific model.
MODEL_REASONING_CONFIG = {
    # GPT 5.2 uses "xhigh" for extended reasoning
    "openai/gpt-5.2": {"param_name": "reasoning_effort", "value": "xhigh"},
    # Claude uses extended thinking with budget_tokens
    # "anthropic/claude-opus-4.5": {"param_name": "thinking", "value": {"type": "enabled", "budget_tokens": 10000}},
    # Gemini uses thinking_config
    # "google/gemini-3-pro-preview": {"param_name": "thinking", "value": {"thinking_budget": 8000}},
}


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