import logging
from .base_tool import BaseTool
from src.query_engines import QueryEngineManager

logger = logging.getLogger(__name__)


class AppManualTool(BaseTool):
    """Collection of tools for the Golf RAG Agent"""

    def __init__(self, query_engine_manager: QueryEngineManager):
        self.qe_manager = query_engine_manager

    @property
    def name(self) -> str:
        return "search_app_manual"

    @property
    def description(self) -> str:
        return """Useful for searching and querying application documentation and user manual.
        This tool can answer questions about:
        - How to use the golf application features
        - Application settings and configuration
        - Feature explanations and tutorials
        - Best practices for using the app
        
        Input should be a natural language question about the application."""

    async def _execute(self, query: str) -> str:
        """Execute search on application documentation and user manual"""

        if not self.qe_manager.app_query_engine:
            return "Application documentation and user manual search is currently unavailable."

        try:
            response = await self.qe_manager.app_query_engine.aquery(query)
            return str(response)
        except Exception as e:
            logger.error(
                f"Error searching application documentation and user manual: {e}"
            )
            return f"Sorry, I encountered an error while searching application documentation and user manual: {str(e)}"
