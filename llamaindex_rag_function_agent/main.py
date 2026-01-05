import asyncio
import json
import time
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from config.settings import GolfAgentConfig
from src.agent_function import GolfRAGAgentFunction
from src.cassandra_client import get_session
from src.chat_history import ChatHistoryManager

logger = logging.getLogger(__name__)

app = FastAPI(title="Guiders AI")


class ChatRequest(BaseModel):
    message: str
    user_id: str
    chat_id: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    print("Starting up...")
    start_time = time.time()
    config = GolfAgentConfig()
    app.state.config = config

    # Validate Supabase credentials
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        print(
            "Warning: Supabase credentials not set. Chat history will not persist."
        )

    # Warm Cassandra connection
    get_session()

    # Initialize chat history manager
    app.state.chat_history = ChatHistoryManager(config)

    # Instantiate agent once
    app.state.agent = GolfRAGAgentFunction(config)
    print("✓ FastAPI server ready")
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    agent = getattr(app.state, "agent", None)
    chat_history_mgr = getattr(app.state, "chat_history", None)

    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not ready")

    if chat_history_mgr is None:
        raise HTTPException(status_code=503, detail="Chat history manager not ready")

    try:
        # Get or create chat
        chat_id = chat_history_mgr.get_or_create_chat(
            user_id=request.user_id,
            chat_id=request.chat_id,
            first_message=request.message if request.chat_id is None else None,
        )

        # Load chat history
        chat_history = chat_history_mgr.get_chat_history(
            chat_id=chat_id, limit=app.state.config.CHAT_HISTORY_LIMIT
        )

        # Initialize message IDs and timestamps
        user_message_id = str(uuid4())
        assistant_message_id = str(uuid4())
        created_user = int(datetime.utcnow().timestamp() * 1000)
        created_assistant = created_user + 1

        # Collect assistant response for saving
        assistant_response_parts = []

        async def token_generator():
            try:
                async for chunk in agent.chat_streaming(
                    request.message,
                    context=None,
                    chat_history=chat_history,
                ):
                    assistant_response_parts.append(chunk)
                    print(f"chunk: {chunk}")
                    yield chunk

                # Streaming completed successfully - save both messages together
                assistant_response = "".join(assistant_response_parts)
                if assistant_response.strip():
                    try:
                        chat_history_mgr.save_conversation(
                            chat_id=chat_id,
                            user_message=request.message,
                            assistant_message=assistant_response,
                            user_message_id=user_message_id,
                            assistant_message_id=assistant_message_id,
                            created_user=created_user,
                            created_assistant=created_assistant,
                        )

                        # Send metadata after tokens are delivered
                        metadata_payload = {
                            "chat_id": str(chat_id),
                            "history_id": str(assistant_message_id),
                            "created": created_assistant,
                        }
                        print(f"metadata_payload: {metadata_payload}")
                        yield f"\n\n[METADATA]{json.dumps(metadata_payload)}"
                    except Exception as save_error:
                        logger.error(f"Failed to save conversation: {save_error}")

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                yield f"[ERROR] {exc}"
                raise

        return StreamingResponse(token_generator(), media_type="text/plain")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
