"""OpenRouter API client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional, Union
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, get_reasoning_config

# Type for message content - can be string or multimodal array
MessageContent = Union[str, List[Dict[str, Any]]]


def build_multimodal_content(text: str, images: Optional[List[str]] = None) -> MessageContent:
    """
    Build multimodal message content with text and optional images.
    
    Args:
        text: The text content of the message
        images: Optional list of base64 data URLs (e.g., "data:image/png;base64,...")
    
    Returns:
        Either a plain string (if no images) or a multimodal content array
    """
    if not images:
        return text
    
    # Build multimodal content array
    content: List[Dict[str, Any]] = [{"type": "text", "text": text}]
    
    for image_url in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    
    return content


async def query_model(
    model: str,
    messages: List[Dict[str, Any]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content' (content can be string or multimodal array)
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    # Add reasoning configuration if available for this model
    reasoning_config = get_reasoning_config(model)
    if reasoning_config:
        param_name = reasoning_config["param_name"]
        param_value = reasoning_config["value"]
        payload[param_name] = param_value

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, Any]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model (content can be string or multimodal array)

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
