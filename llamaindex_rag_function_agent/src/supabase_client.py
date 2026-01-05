import logging
from functools import lru_cache
from typing import Optional
from supabase import create_client, Client
from config.settings import GolfAgentConfig

logger = logging.getLogger(__name__)

_config = GolfAgentConfig()
_supabase_client: Optional[Client] = None


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create (or reuse) a Supabase client."""
    global _supabase_client

    if _supabase_client:
        return _supabase_client

    if not _config.SUPABASE_URL or not _config.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY are required")

    try:
        _supabase_client = create_client(_config.SUPABASE_URL, _config.SUPABASE_KEY)
        logger.info("✓ Supabase client initialized")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise
