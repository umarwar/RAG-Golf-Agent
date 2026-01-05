import os
import logging
from pinecone import Pinecone
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.replicate import Replicate
from config.settings import GolfAgentConfig

# logger = logging.getLogger(__name__)


class QueryEngineManager:
    """Manages multiple query engines for different data sources"""

    def __init__(self, config: GolfAgentConfig):
        self.config = config
        self._setup_global_settings()
        self.golf_query_engine = self._setup_golf_courses_engine()
        self.app_query_engine = self._setup_app_manual_engine()

    def _setup_global_settings(self):
        """Setup global LlamaIndex settings"""
        os.environ["OPENAI_API_KEY"] = self.config.OPENAI_API_KEY

        # Setup embedding model
        embed_model = OpenAIEmbedding(
            model=self.config.EMBEDDING_MODEL,
            dimensions=self.config.EMBEDDING_DIMENSION,
            api_key=self.config.OPENAI_API_KEY,
        )
        Settings.embed_model = embed_model

        print("✓ Global settings configured")

    def _setup_golf_courses_engine(self):
        """Setup query engine for golf courses data"""
        try:
            pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
            golf_index = pc.Index(host=self.config.GOLF_INDEX_HOST)

            vector_store = PineconeVectorStore(
                pinecone_index=golf_index,
                namespace=self.config.GOLF_NAMESPACE,
                api_key=self.config.PINECONE_API_KEY,
            )

            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

            query_engine = index.as_query_engine(
                similarity_top_k=self.config.SIMILARITY_TOP_K,
                response_mode="compact",
                # streaming=True,
            )

            print("✓ Golf courses query engine initialized")
            return query_engine

        except Exception as e:
            print(f"Failed to initialize golf courses engine: {e}")
            return None

    def _setup_app_manual_engine(self):
        """Setup query engine for app documentation"""
        try:
            pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
            app_index = pc.Index(host=self.config.APP_INDEX_HOST)

            vector_store = PineconeVectorStore(
                pinecone_index=app_index, api_key=self.config.PINECONE_API_KEY
            )
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

            query_engine = index.as_query_engine(
                similarity_top_k=self.config.SIMILARITY_TOP_K,
                response_mode="compact",
                # streaming=True,
            )

            print("✓ App manual query engine initialized")
            return query_engine

        except Exception as e:
            print(f"Failed to initialize app manual engine: {e}")
            return None
