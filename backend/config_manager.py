"""Configuration management with JSON file storage."""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Default values (matching config.py defaults)
DEFAULT_COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "deepseek/deepseek-v3.2"
]

DEFAULT_CHAIRMAN_MODEL = "openai/gpt-5.2"
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_MODEL_REASONING_CONFIG = {
    "openai/gpt-5.2": {"param_name": "reasoning_effort", "value": "high"},
}

CONFIG_FILE = "data/config.json"


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path("data").mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """
    Load configuration from JSON file, with fallback to defaults.
    
    Returns:
        Configuration dictionary
    """
    ensure_data_dir()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Validate and merge with defaults
                return {
                    "council_models": config.get("council_models", DEFAULT_COUNCIL_MODELS),
                    "chairman_model": config.get("chairman_model", DEFAULT_CHAIRMAN_MODEL),
                    "default_reasoning_effort": config.get("default_reasoning_effort", DEFAULT_REASONING_EFFORT),
                    "model_reasoning_config": config.get("model_reasoning_config", DEFAULT_MODEL_REASONING_CONFIG),
                }
        except Exception as e:
            print(f"Warning: Failed to load config from {CONFIG_FILE}: {e}")
    
    # Return defaults
    return {
        "council_models": DEFAULT_COUNCIL_MODELS,
        "chairman_model": DEFAULT_CHAIRMAN_MODEL,
        "default_reasoning_effort": DEFAULT_REASONING_EFFORT,
        "model_reasoning_config": DEFAULT_MODEL_REASONING_CONFIG,
    }


def save_config(config: Dict[str, Any]) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary to save
    """
    ensure_data_dir()
    
    # Validate configuration
    if not isinstance(config.get("council_models"), list):
        raise ValueError("council_models must be a list")
    if not config.get("council_models"):
        raise ValueError("council_models cannot be empty")
    if not isinstance(config.get("chairman_model"), str):
        raise ValueError("chairman_model must be a string")
    if config.get("chairman_model") not in config.get("council_models", []):
        raise ValueError("chairman_model must be one of the council_models")
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_config() -> Dict[str, Any]:
    """Get current configuration."""
    return load_config()


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update configuration with provided values.
    
    Args:
        updates: Dictionary with configuration updates
        
    Returns:
        Updated configuration dictionary
    """
    current = load_config()
    current.update(updates)
    save_config(current)
    return current
