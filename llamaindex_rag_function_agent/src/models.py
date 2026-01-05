from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    user_id: str
    chat_id: Optional[str] = None


class ChatListRequest(BaseModel):
    user_id: str


class ChatListResponse(BaseModel):
    user_id: UUID
    chat_id: UUID
    created: datetime
    title: str


class ChatMessagesRequest(BaseModel):
    chat_id: str


class ChatMessageResponse(BaseModel):
    chat_id: UUID
    history_id: UUID
    role: str
    content: str
    created: datetime
