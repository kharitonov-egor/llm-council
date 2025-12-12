"""OpenRouter API client for making LLM requests."""

import httpx
import logging
import time
from typing import List, Dict, Any, Optional, Union
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, get_reasoning_config

# Set up logging
logger = logging.getLogger(__name__)

# ANSI color codes for log output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    # Request/Send colors
    SEND = "\033[93m"      # Yellow - sending
    # Response/Receive colors  
    RECV = "\033[92m"      # Green - receiving
    # Error colors
    ERROR = "\033[91m"     # Red - errors
    # Info colors
    INFO = "\033[96m"      # Cyan - general info
    MODEL = "\033[95m"     # Magenta - model names

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
        logger.info(f"{Colors.INFO}[{model}] Reasoning: {param_name}={param_value}{Colors.RESET}")

    # Log request details
    msg_preview = str(messages[0].get('content', ''))[:100] if messages else ''
    has_images = any(
        isinstance(m.get('content'), list) and 
        any(c.get('type') == 'image_url' for c in m.get('content', []))
        for m in messages
    )
    logger.info(f"{Colors.SEND}>>> [{model}] SENDING request (images: {has_images}, timeout: {timeout}s){Colors.RESET}")
    logger.debug(f"[{model}] Message preview: {msg_preview}...")

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            elapsed = time.time() - start_time
            data = response.json()
            message = data['choices'][0]['message']

            # Log response details
            content_length = len(message.get('content', '') or '')
            has_reasoning = message.get('reasoning_details') is not None
            logger.info(f"{Colors.RECV}<<< [{model}] RECEIVED in {elapsed:.2f}s (chars: {content_length}, reasoning: {has_reasoning}){Colors.RESET}")

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except httpx.TimeoutException:
        elapsed = time.time() - start_time
        logger.error(f"{Colors.ERROR}!!! [{model}] TIMEOUT after {elapsed:.2f}s{Colors.RESET}")
        return None
    except httpx.HTTPStatusError as e:
        elapsed = time.time() - start_time
        logger.error(f"{Colors.ERROR}!!! [{model}] HTTP {e.response.status_code} after {elapsed:.2f}s: {e.response.text[:200]}{Colors.RESET}")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"{Colors.ERROR}!!! [{model}] ERROR after {elapsed:.2f}s: {type(e).__name__}: {e}{Colors.RESET}")
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

    logger.info(f"{Colors.INFO}{'='*60}{Colors.RESET}")
    logger.info(f"{Colors.INFO}Querying {len(models)} models in parallel{Colors.RESET}")
    start_time = time.time()

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    successful = sum(1 for r in responses if r is not None)
    logger.info(f"{Colors.INFO}Parallel query complete in {elapsed:.2f}s ({successful}/{len(models)} succeeded){Colors.RESET}")
    logger.info(f"{Colors.INFO}{'='*60}{Colors.RESET}")

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
