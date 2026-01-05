import asyncio
import json
import time
import logging
from datetime import datetime
from uuid import uuid4
from typing import List
from uuid import UUID

from fastapi import FastAPI, HTTPException
from sse_starlette.sse import EventSourceResponse

from config.settings import GolfAgentConfig
from src.agent_function import GolfRAGAgentFunction
from src.cassandra_client import get_session
from src.chat_history import ChatHistoryManager
from src.models import (
    ChatRequest,
    ChatListRequest,
    ChatMessagesRequest,
    ChatListResponse,
    ChatMessageResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Guiders AI")


@app.on_event("startup")
async def startup_event():
    print("Starting up...")
    start_time = time.time()
    config = GolfAgentConfig()
    app.state.config = config

    # Validate Supabase credentials
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        print("Warning: Supabase credentials not set. Chat history will not persist.")

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

    async def event_generator():
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

            user_message_id = str(uuid4())
            assistant_message_id = str(uuid4())
            created_user = int(datetime.utcnow().timestamp() * 1000)
            created_assistant = created_user + 1

            assistant_response_parts = []

            try:
                async for chunk in agent.chat_streaming(
                    request.message,
                    context=None,
                    chat_history=chat_history,
                ):
                    print(f"chunk: {chunk}")
                    assistant_response_parts.append(chunk)
                    yield {
                        "event": "message",
                        "data": chunk,
                    }

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

                        # Send metadata as separate SSE event
                        metadata_payload = {
                            "chat_id": str(chat_id),
                            "history_id": str(assistant_message_id),
                            "created": created_assistant,
                        }
                        yield {
                            "event": "metadata",
                            "data": json.dumps(metadata_payload),
                        }
                    except Exception as save_error:
                        logger.error(f"Failed to save conversation: {save_error}")
                        yield {
                            "event": "error",
                            "data": json.dumps(
                                {
                                    "error": f"Failed to save conversation: {str(save_error)}"
                                }
                            ),
                        }

            except asyncio.CancelledError:
                # Client disconnected, clean up gracefully
                raise
            except Exception as exc:
                logger.error(f"Error during streaming: {exc}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(exc)}),
                }

        except ValueError as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }
        except Exception as e:
            logger.error(f"Unexpected error in chat_stream: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Internal error: {str(e)}"}),
            }

    return EventSourceResponse(event_generator())


@app.post("/chat/all", response_model=List[ChatListResponse])
async def get_all_chats(request: ChatListRequest):
    """
    Get all chats for a given user.

    Returns a list of chats with chat_id, user_id, created timestamp, and title.
    """
    chat_history_mgr = getattr(app.state, "chat_history", None)

    if chat_history_mgr is None:
        raise HTTPException(status_code=503, detail="Chat history manager not ready")

    try:
        chats = chat_history_mgr.get_all_chats(request.user_id)

        response_list = []
        for chat in chats:
            # Parse created timestamp - handle string, datetime, or None
            created = chat.get("created")
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    created = datetime.utcnow()
            elif isinstance(created, datetime):
                pass
            elif created is None:
                created = datetime.utcnow()

            response_list.append(
                ChatListResponse(
                    user_id=UUID(chat["user_id"]),
                    chat_id=UUID(chat["chat_id"]),
                    created=created,
                    title=chat.get("title") or "Untitled Chat",
                )
            )

        return response_list
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching chats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/chat/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(request: ChatMessagesRequest):
    """
    Get all messages for a given chat.

    Returns a list of messages with chat_id, history_id, role, content, and created timestamp.
    """
    chat_history_mgr = getattr(app.state, "chat_history", None)

    if chat_history_mgr is None:
        raise HTTPException(status_code=503, detail="Chat history manager not ready")

    try:
        messages = chat_history_mgr.get_all_messages(request.chat_id)

        response_list = []
        for msg in messages:
            # Parse created timestamp - handle string, datetime, or None
            created = msg.get("created")
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    created = datetime.utcnow()
            elif isinstance(created, datetime):
                pass
            elif created is None:
                created = datetime.utcnow()

            response_list.append(
                ChatMessageResponse(
                    chat_id=UUID(msg["chat_id"]),
                    history_id=UUID(msg["history_id"]),
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    created=created,
                )
            )

        return response_list
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
