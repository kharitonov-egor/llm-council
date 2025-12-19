"""Configuration for the LLM Council."""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from .config_manager import (
    load_config,
    DEFAULT_COUNCIL_MODELS,
    DEFAULT_CHAIRMAN_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_MODEL_REASONING_CONFIG,
)

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"


def get_runtime_config() -> Dict[str, Any]:
    """Load the current runtime configuration."""
    try:
        return load_config()
    except Exception:
        return {
            "council_models": DEFAULT_COUNCIL_MODELS,
            "chairman_model": DEFAULT_CHAIRMAN_MODEL,
            "default_reasoning_effort": DEFAULT_REASONING_EFFORT,
            "model_reasoning_config": DEFAULT_MODEL_REASONING_CONFIG,
        }


def get_reasoning_config(model: str, config: Optional[Dict[str, Any]] = None) -> dict | None:
    """
    Get the reasoning configuration for a specific model.

    Args:
        model: The model identifier (e.g., "openai/gpt-5.2")
        config: Optional configuration snapshot to use

    Returns:
        Dict with 'param_name' and 'value' keys, or None if reasoning is disabled
    """
    runtime_config = config or get_runtime_config()
    model_reasoning_config = runtime_config.get("model_reasoning_config") or {}
    default_reasoning_effort = runtime_config.get("default_reasoning_effort")

    # Check for model-specific override
    if model in model_reasoning_config:
        model_config = model_reasoning_config[model]
        if model_config is None or model_config.get("value") is None:
            return None
        return model_config

    # Use default if no override and default is set
    if default_reasoning_effort is not None:
        return {"param_name": "reasoning_effort", "value": default_reasoning_effort}

    return None
