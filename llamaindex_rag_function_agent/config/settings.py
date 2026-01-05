import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class GolfAgentConfig:
    """Central configuration for the Golf RAG Agent"""

    # API Keys
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

    CASSANDRA_USERNAME = os.environ.get("CASSANDRA_USERNAME")
    CASSANDRA_PASSWORD = os.environ.get("CASSANDRA_PASS")

    # Pinecone Indexes
    GOLF_INDEX_NAME = os.environ.get("GOLF_INDEX_NAME")
    GOLF_INDEX_HOST = os.environ.get("GOLF_INDEX_HOST")
    GOLF_NAMESPACE = os.environ.get("GOLF_NAMESPACE")

    APP_INDEX_NAME = os.environ.get("APP_INDEX_NAME")
    APP_INDEX_HOST = os.environ.get("APP_INDEX_HOST")

    # Model Settings
    EMBEDDING_MODEL = "text-embedding-3-large"
    EMBEDDING_DIMENSION = 1536
    # LLM_MODEL = "gemini-2.5-flash"
    LLM_MODEL = "gpt-4.1-mini"
    LLM_TEMPERATURE = 0.1

    # Agent Setting
    SIMILARITY_TOP_K = 5
    AGENT_MAX_ITERATIONS = 5
    CHAT_HISTORY_LIMIT = 14

    # Supabase Configuration
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
