import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from llama_index.core.llms import ChatMessage, MessageRole
from supabase import Client

from src.supabase_client import get_supabase_client
from config.settings import GolfAgentConfig

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """Manages chat history persistence in Supabase"""

    def __init__(self, config: GolfAgentConfig):
        self.config = config
        self.client: Client = get_supabase_client()

    def get_or_create_chat(
        self,
        user_id: str,
        chat_id: Optional[str] = None,
        first_message: Optional[str] = None,
    ) -> str:
        """
        Get existing chat or create a new one.

        Args:
            user_id: UUID string of the user
            chat_id: Optional UUID string of existing chat
            first_message: Optional first message to set as chat title (for new chats)

        Returns:
            chat_id as string
        """
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError(f"Invalid user_id format: {user_id}")

        # If chat_id provided, check if it exists
        if chat_id:
            try:
                UUID(chat_id)
                result = (
                    self.client.table("chat_by_user")
                    .select("chat_id")
                    .eq("chat_id", chat_id)
                    .execute()
                )

                if result.data:
                    return chat_id
                else:
                    raise ValueError(f"Chat {chat_id} not found")
            except ValueError as e:
                raise ValueError(f"Invalid chat_id format: {chat_id}") from e

        # Create new chat with title from first message
        new_chat_id = uuid4()
        title = None
        if first_message:
            title = first_message[:100].strip()
            if len(first_message) > 100:
                title += "..."

        result = (
            self.client.table("chat_by_user")
            .insert(
                {
                    "chat_id": str(new_chat_id),
                    "user_id": str(user_uuid),
                    "title": title,
                }
            )
            .execute()
        )

        if not result.data:
            raise RuntimeError("Failed to create new chat")

        return str(new_chat_id)

    def get_chat_history(self, chat_id: str, limit: int = 10) -> List[ChatMessage]:
        """
        Fetch chat history from database and convert to ChatMessage objects.

        Args:
            chat_id: UUID string of the chat
            limit: Maximum number of messages to retrieve

        Returns:
            List of ChatMessage objects, ordered by created timestamp
        """
        try:
            chat_uuid = UUID(chat_id)
        except ValueError:
            raise ValueError(f"Invalid chat_id format: {chat_id}")

        result = (
            self.client.table("history_by_chat")
            .select("role, content, created")
            .eq("chat_id", str(chat_uuid))
            .order("created", desc=True)
            .limit(limit)
            .execute()
        )

        messages = []
        for row in result.data:
            role_str = row.get("role", "").lower()
            content = row.get("content", "")

            # Map database role to LlamaIndex MessageRole
            if role_str == "user":
                role = MessageRole.USER
            elif role_str == "assistant":
                role = MessageRole.ASSISTANT
            elif role_str == "system":
                role = MessageRole.SYSTEM
            else:
                logger.warning(f"Unknown role '{role_str}', defaulting to USER")
                role = MessageRole.USER

            messages.append(ChatMessage(role=role, content=content))

        messages.reverse()

        return messages

    def save_conversation(
        self,
        chat_id: str,
        user_message: str,
        assistant_message: str,
        user_message_id: str,
        assistant_message_id: str,
        created_user: int,
        created_assistant: int,
    ) -> None:
        """
        Save both user and assistant messages together with specified IDs and timestamps.

        Args:
            chat_id: UUID string of the chat
            user_message: User's message content
            assistant_message: Assistant's response content
            user_message_id: UUID string for user message history_id
            assistant_message_id: UUID string for assistant message history_id
            created_user: Timestamp in milliseconds for user message
            created_assistant: Timestamp in milliseconds for assistant message
        """
        try:
            chat_uuid = UUID(chat_id)
            user_history_uuid = UUID(user_message_id)
            assistant_history_uuid = UUID(assistant_message_id)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}")

        # Convert timestamps from milliseconds to datetime objects
        created_user_dt = datetime.fromtimestamp(created_user / 1000, tz=timezone.utc)
        created_assistant_dt = datetime.fromtimestamp(
            created_assistant / 1000, tz=timezone.utc
        )

        # Save user message
        user_result = (
            self.client.table("history_by_chat")
            .insert(
                {
                    "chat_id": str(chat_uuid),
                    "history_id": str(user_history_uuid),
                    "role": "user",
                    "content": user_message,
                    "created": created_user_dt.isoformat(),
                }
            )
            .execute()
        )

        if not user_result.data:
            raise RuntimeError(f"Failed to save user message to chat {chat_id}")

        # Save assistant message
        assistant_result = (
            self.client.table("history_by_chat")
            .insert(
                {
                    "chat_id": str(chat_uuid),
                    "history_id": str(assistant_history_uuid),
                    "role": "assistant",
                    "content": assistant_message,
                    "created": created_assistant_dt.isoformat(),
                }
            )
            .execute()
        )

        if not assistant_result.data:
            logger.error(f"Failed to save assistant message to chat {chat_id}")
            raise RuntimeError(f"Failed to save assistant message to chat {chat_id}")

    def get_all_chats(self, user_id: str) -> List[dict]:
        """
        Fetch all chats for a given user from chat_by_user table.

        Args:
            user_id: UUID string of the user

        Returns:
            List of dictionaries with chat_id, user_id, created, and title
        """
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError(f"Invalid user_id format: {user_id}")

        result = (
            self.client.table("chat_by_user")
            .select("chat_id, user_id, created, title")
            .eq("user_id", str(user_uuid))
            .order("created", desc=True)
            .execute()
        )

        return result.data if result.data else []

    def get_all_messages(self, chat_id: str) -> List[dict]:
        """
        Fetch all messages for a given chat from history_by_chat table.

        Args:
            chat_id: UUID string of the chat

        Returns:
            List of dictionaries with chat_id, history_id, role, content, and created
        """
        try:
            chat_uuid = UUID(chat_id)
        except ValueError:
            raise ValueError(f"Invalid chat_id format: {chat_id}")

        result = (
            self.client.table("history_by_chat")
            .select("chat_id, history_id, role, content, created")
            .eq("chat_id", str(chat_uuid))
            .order("created", desc=False)
            .execute()
        )

        return result.data if result.data else []
