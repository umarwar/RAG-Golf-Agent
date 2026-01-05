import logging
from typing import List, Dict

from .base_tool import BaseTool
from src.cassandra_client import fetch_rows

logger = logging.getLogger(__name__)

SCORECARD_QUERY = "SELECT * FROM igolf_scorecard_by_course WHERE id_course = %s"


def _parse_csv_numbers(value: str) -> List[int]:
    if not value:
        return []
    return [int(x) for x in value.split(",") if x.strip()]


def _generate_markdown_scorecard(rows: List[Dict]) -> str:
    if not rows:
        return "No scorecard information was found for that course."

    row = rows[0]
    men_hcp = _parse_csv_numbers(row.get("men_hcp_hole", ""))
    men_par = _parse_csv_numbers(row.get("men_par_hole", ""))
    women_hcp = _parse_csv_numbers(row.get("wmn_hcp_hole", ""))
    women_par = _parse_csv_numbers(row.get("wmn_par_hole", ""))

    num_holes = max(
        len([p for p in men_par if p > 0]),
        len([p for p in women_par if p > 0]),
        len([p for p in men_hcp if p > 0]),
        len([p for p in women_hcp if p > 0]),
    )
    if num_holes == 0:
        return "Scorecard data was found but no hole-by-hole values were populated."

    def _pad(values: List[int]) -> List[str]:
        padded = values[:num_holes]
        return [str(v) for v in padded + [0] * (num_holes - len(padded))]

    men_hcp = _pad(men_hcp)
    men_par = _pad(men_par)
    women_hcp = _pad(women_hcp)
    women_par = _pad(women_par)

    # column widths
    max_men_par = max(len(v) for v in men_par) if men_par else 1
    max_men_hcp = max(len(v) for v in men_hcp) if men_hcp else 1
    max_wmn_par = max(len(v) for v in women_par) if women_par else 1
    max_wmn_hcp = max(len(v) for v in women_hcp) if women_hcp else 1

    def fmt(val: str, width: int) -> str:
        return val.ljust(width)

    header = (
        "| Holes | Men Par | Men Hcp | Women Par | Women Hcp |\n"
        "|-------|---------|---------|-----------|-----------|"
    )
    rows_md = []
    for idx in range(num_holes):
        rows_md.append(
            f"| {idx + 1:>2} "
            f"| {fmt(men_par[idx], max_men_par)} "
            f"| {fmt(men_hcp[idx], max_men_hcp)} "
            f"| {fmt(women_par[idx], max_wmn_par)} "
            f"| {fmt(women_hcp[idx], max_wmn_hcp)} |"
        )

    footer = []
    for label, key in [
        ("Par In", "men_par_in"),
        ("Par Out", "men_par_out"),
        ("Par Total", "men_par_total"),
    ]:
        men_val = str(row.get(key, "")).ljust(max_men_par)
        women_key = key.replace("men_", "wmn_")
        women_val = str(row.get(women_key, "")).ljust(max_wmn_par)
        footer.append(
            f"| **{label}** "
            f"| {men_val} | {' ' * max_men_hcp} "
            f"| {women_val} | {' ' * max_wmn_hcp} |"
        )

    return "\n".join(
        [
            "### Scorecard Details",
            header,
            *rows_md,
            *footer,
        ]
    )


class ScorecardTool(BaseTool):
    """Search scorecard data for a given course ID."""

    @property
    def name(self) -> str:
        return "search_scorecards"

    @property
    def description(self) -> str:
        return """Use this tool to retrieve scorecard hole information, par totals, and rating data for a given course.
Input should be the course identifier (id_course) as a string."""

    async def _execute(self, course_id: str) -> str:
        """Retrieve scorecard data for a specific golf course.

        Args:
            course_id (str): The course identifier (id_course) as a string.

        Returns:
            str: A markdown-formatted string containing scorecard details including
                 hole-by-hole par and handicap information for both men and women.
        """
        try:
            rows = fetch_rows(SCORECARD_QUERY, [course_id])
            return _generate_markdown_scorecard(rows)
        except Exception as exc:
            logger.error("Scorecard lookup failed: %s", exc, exc_info=True)
            return (
                "I couldn't retrieve scorecard data right now. Please try again later."
            )
