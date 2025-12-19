"""FastAPI backend for LLM Council."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage3_synthesize_final, calculate_aggregate_rankings, parse_ranking_from_text, build_stage2_prompt
from .openrouter import query_model, build_multimodal_content
from .config_manager import get_config, update_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Suppress noisy httpx logs (we have our own request/response logging)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    images: List[str] = []  # Base64 data URLs (e.g., "data:image/png;base64,...")


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0
    image_count = len(request.images) if request.images else 0
    
    logger.info(f"New message in {conversation_id[:8]}... (images: {image_count}, first: {is_first_message})")
    logger.info(f"Query: {request.content[:100]}{'...' if len(request.content) > 100 else ''}")

    # Add user message (with images if present)
    storage.add_user_message(conversation_id, request.content, request.images)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)
        logger.info(f"Generated title: {title}")

    config_snapshot = get_config()

    # Run the 3-stage council process (with images)
    logger.info("Starting 3-stage council process...")
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content, request.images if request.images else None, config=config_snapshot
    )
    logger.info("Council process complete")

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get images (or None if empty)
    images = request.images if request.images else None
    image_count = len(images) if images else 0
    
    logger.info(f"[STREAM] New message in {conversation_id[:8]}... (images: {image_count}, first: {is_first_message})")
    logger.info(f"[STREAM] Query: {request.content[:100]}{'...' if len(request.content) > 100 else ''}")

    config_snapshot = get_config()
    council_models = config_snapshot["council_models"]
    chairman_model = config_snapshot["chairman_model"]

    async def event_generator():
        try:
            # Add user message (with images if present)
            storage.add_user_message(conversation_id, request.content, request.images)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses (with images) - stream individual responses
            logger.info("[STREAM] Stage 1: Collecting individual responses...")
            
            # Send start event with list of pending models
            yield f"data: {json.dumps({'type': 'stage1_start', 'models': council_models})}\n\n"
            
            # Build multimodal content for the query
            content = build_multimodal_content(request.content, images)
            messages = [{"role": "user", "content": content}]
            
            # Create tasks for all models
            async def query_model_with_name(model):
                """Query a model and return (model, response) tuple."""
                response = await query_model(model, messages, config=config_snapshot)
                return (model, response)
            
            # Start all queries in parallel
            tasks = [asyncio.create_task(query_model_with_name(model)) for model in council_models]
            
            # Collect results as they complete
            stage1_results = []
            for coro in asyncio.as_completed(tasks):
                model, response = await coro
                if response is not None:
                    result = {
                        "model": model,
                        "response": response.get('content', '')
                    }
                    stage1_results.append(result)
                    logger.info(f"[STREAM] Stage 1: {model} responded")
                    # Emit individual response event
                    yield f"data: {json.dumps({'type': 'stage1_response', 'data': result})}\n\n"
                else:
                    logger.warning(f"[STREAM] Stage 1: {model} failed")
                    # Emit failure event so frontend knows this model won't respond
                    yield f"data: {json.dumps({'type': 'stage1_response', 'data': {'model': model, 'response': None, 'failed': True}})}\n\n"
            
            logger.info(f"[STREAM] Stage 1 complete: {len(stage1_results)} responses")
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings (with images for context) - stream individual rankings
            logger.info("[STREAM] Stage 2: Collecting peer rankings...")
            
            # Build the ranking prompt and get label mapping
            ranking_prompt, label_to_model = build_stage2_prompt(request.content, stage1_results, images)
            
            # Send start event with pending models and label mapping
            yield f"data: {json.dumps({'type': 'stage2_start', 'models': council_models, 'metadata': {'label_to_model': label_to_model}})}\n\n"
            
            # Build multimodal content for ranking
            ranking_content = build_multimodal_content(ranking_prompt, images)
            ranking_messages = [{"role": "user", "content": ranking_content}]
            
            # Create tasks for all models
            async def query_ranking_with_name(model):
                """Query a model for ranking and return (model, response) tuple."""
                response = await query_model(model, ranking_messages, config=config_snapshot)
                return (model, response)
            
            # Start all ranking queries in parallel
            ranking_tasks = [asyncio.create_task(query_ranking_with_name(model)) for model in council_models]
            
            # Collect results as they complete
            stage2_results = []
            for coro in asyncio.as_completed(ranking_tasks):
                model, response = await coro
                if response is not None:
                    full_text = response.get('content', '')
                    parsed = parse_ranking_from_text(full_text)
                    result = {
                        "model": model,
                        "ranking": full_text,
                        "parsed_ranking": parsed
                    }
                    stage2_results.append(result)
                    logger.info(f"[STREAM] Stage 2: {model} ranked")
                    # Emit individual ranking event
                    yield f"data: {json.dumps({'type': 'stage2_response', 'data': result})}\n\n"
                else:
                    logger.warning(f"[STREAM] Stage 2: {model} failed")
                    # Emit failure event
                    yield f"data: {json.dumps({'type': 'stage2_response', 'data': {'model': model, 'ranking': None, 'failed': True}})}\n\n"
            
            # Calculate aggregate rankings
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            
            logger.info(f"[STREAM] Stage 2 complete: {len(stage2_results)} rankings")
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer (with images for context)
            logger.info("[STREAM] Stage 3: Synthesizing final response...")
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content,
                stage1_results,
                stage2_results,
                images,
                chairman_model=chairman_model,
                config=config_snapshot
            )
            logger.info("[STREAM] Stage 3 complete")
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                logger.info(f"[STREAM] Generated title: {title}")
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            logger.info("[STREAM] Council process complete")
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            logger.error(f"[STREAM] Error: {type(e).__name__}: {e}")
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


class UpdateConfigRequest(BaseModel):
    """Request to update configuration."""
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None
    default_reasoning_effort: Optional[str] = None
    model_reasoning_config: Optional[Dict[str, Any]] = None


@app.get("/api/config")
async def get_configuration():
    """Get current configuration."""
    return get_config()


@app.put("/api/config")
async def update_configuration(request: UpdateConfigRequest):
    """Update configuration."""
    # Get which fields were explicitly provided in the request
    provided_fields = request.model_fields_set
    
    updates = {}
    if "council_models" in provided_fields:
        updates["council_models"] = request.council_models
    if "chairman_model" in provided_fields:
        updates["chairman_model"] = request.chairman_model
    if "default_reasoning_effort" in provided_fields:
        updates["default_reasoning_effort"] = request.default_reasoning_effort
    if "model_reasoning_config" in provided_fields:
        updates["model_reasoning_config"] = request.model_reasoning_config
    
    try:
        updated_config = update_config(updates)
        logger.info("Configuration saved successfully.")
        return updated_config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
