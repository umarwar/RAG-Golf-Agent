import logging
from typing import List, Dict

from .base_tool import BaseTool
from src.cassandra_client import fetch_rows

logger = logging.getLogger(__name__)

TEE_QUERY = "SELECT * FROM igolf_tee_detail_by_course WHERE id_course = %s"


def _generate_markdown_tees(rows: List[Dict]) -> str:
    if not rows:
        return "No tee details were found for that course."

    tees = {}
    num_holes = 0

    for row in rows:
        yds_raw = row.get("ydshole", "")
        if not yds_raw:
            continue
        yardages = [int(val) for val in yds_raw.split(",") if val.strip()]
        if not yardages:
            continue
        num_holes = max(num_holes, len(yardages))
        tees[row.get("teename", "Unnamed Tee")] = {
            "yardages": yardages,
            "total": row.get("ydstotal"),
            "men": (row.get("ratingmen"), row.get("slopemen")),
            "women": (row.get("ratingwomen"), row.get("slopewomen")),
        }

    if not tees or num_holes == 0:
        return "Tee details were available but could not be parsed."

    tee_names = list(tees.keys())
    header = [
        "| Hole | " + " | ".join(tee_names) + " |",
        "|------|" + "|".join(["------"] * len(tee_names)) + "|",
    ]

    rows_md = []
    for idx in range(num_holes):
        cells = []
        for tee in tee_names:
            yardages = tees[tee]["yardages"]
            val = yardages[idx] if idx < len(yardages) else ""
            cells.append(str(val))
        rows_md.append(f"| {idx + 1:>2} | " + " | ".join(cells) + " |")

    total_row = (
        "| Total | "
        + " | ".join([str(tees[tee]["total"] or "") for tee in tee_names])
        + " |"
    )

    rating_row = (
        "| Men CR/Slope | "
        + " | ".join(
            [
                f"{(tees[tee]['men'][0] or 'N/A')}/{(tees[tee]['men'][1] or 'N/A')}"
                for tee in tee_names
            ]
        )
        + " |"
    )

    women_row = (
        "| Women CR/Slope | "
        + " | ".join(
            [
                f"{(tees[tee]['women'][0] or 'N/A')}/{(tees[tee]['women'][1] or 'N/A')}"
                for tee in tee_names
            ]
        )
        + " |"
    )

    return "\n".join(
        ["### Tee Details", *header, *rows_md, total_row, rating_row, women_row]
    )


class TeeDetailsTool(BaseTool):
    """Search tee detail data for a given course ID."""

    @property
    def name(self) -> str:
        return "search_tee_details"

    @property
    def description(self) -> str:
        return """Use this tool to list tee colors, yardages, and ratings for a given course.
Input should be the course identifier (id_course) as a string."""

    async def _execute(self, course_id: str) -> str:
        """Retrieve tee detail data for a specific golf course.

        Args:
            course_id (str): The course identifier (id_course) as a string.

        Returns:
            str: A markdown-formatted string containing tee details including
                 yardages, course ratings, and slope ratings for each tee color.
        """
        try:
            rows = fetch_rows(TEE_QUERY, [course_id])
            return _generate_markdown_tees(rows)
        except Exception as exc:
            logger.error("Tee detail lookup failed: %s", exc, exc_info=True)
            return (
                "I couldn't retrieve tee information right now. Please try again later."
            )
