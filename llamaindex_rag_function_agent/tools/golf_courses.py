import logging
from .base_tool import BaseTool
from src.query_engines import QueryEngineManager

logger = logging.getLogger(__name__)


class GolfCoursesTool(BaseTool):
    """Collection of tools for the Golf RAG Agent"""

    def __init__(self, query_engine_manager: QueryEngineManager):
        self.qe_manager = query_engine_manager

    @property
    def name(self) -> str:
        return "search_golf_courses"

    @property
    def description(self) -> str:
        return """Useful for searching and querying information about golf courses.
        This tool can answer questions about:
        - Golf course locations, addresses, and contact information
        - Course types (public, private, etc.)
        - Number of holes and course layouts
        - Golf course recommendations based on location
        
        Input should be a natural language question about golf courses."""

    async def _execute(self, query: str) -> str:
        """Execute search on golf courses data"""

        if not self.qe_manager.golf_query_engine:
            return "Golf courses search is currently unavailable."

        try:
            response = await self.qe_manager.golf_query_engine.aquery(query)
            summary = str(response)

            if getattr(response, "source_nodes", None):
                lines = [summary, "\nTop course matches:"]
                for node in response.source_nodes[:5]:
                    meta = node.metadata or {}
                    course_name = meta.get("courseName", "Unknown course")
                    course_id = meta.get("id_course", "N/A")
                    city = meta.get("city", "")
                    state = meta.get("state", "")
                    latitude = meta.get("latitude", "")
                    longitude = meta.get("longitude", "")
                    lines.append(
                        f"- {course_name} (id_course: {course_id})"
                        + (f" — {city}, {state}" if city or state else "")
                        + (
                            f" — {latitude}, {longitude}"
                            if latitude or longitude
                            else ""
                        )
                    )
                return "\n".join(lines)

            return summary
        except Exception as e:
            logger.error(f"Error searching golf courses: {e}")
            return (
                f"Sorry, I encountered an error while searching golf courses: {str(e)}"
            )
