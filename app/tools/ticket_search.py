
import json
from pathlib import Path
from typing import Any

from app.tools.enterprise_data import get_service


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "tickets.json"
)


def search_change_tickets(keyword: str) -> dict[str, Any]:
    """
    Search incident tickets by keyword.

    Resolves exact service names to service IDs before searching.
    Searches ticket ID, title, service ID, status, severity,
    summary and tags.
    """

    # Validate the input.
    if not isinstance(keyword, str) or not keyword.strip():
        return {
            "found": False,
            "query": keyword,
            "count": 0,
            "tickets": [],
            "message": "Please provide a valid search keyword."
        }

    original_keyword = keyword.strip()

    if len(original_keyword) > 100:
        return {
            "found": False,
            "query": original_keyword,
            "count": 0,
            "tickets": [],
            "message": "Search keyword must not exceed 100 characters."
        }

    search_term = original_keyword.casefold()

    # Resolve an exact service name or ID to its service record.
    service = get_service(original_keyword)

    search_terms = {search_term}

    if service:
        search_terms.add(service["service_id"].casefold())
        search_terms.add(service["name"].casefold())

    # Load incident tickets.
    with DATA_PATH.open("r", encoding="utf-8") as file:
        tickets = json.load(file)

    matches = []

    # Search across relevant ticket fields.
    for ticket in tickets:
        searchable_text = " ".join([
            str(ticket.get("ticket_id", "")),
            str(ticket.get("title", "")),
            str(ticket.get("service_id", "")),
            str(ticket.get("status", "")),
            str(ticket.get("severity", "")),
            str(ticket.get("summary", "")),
            " ".join(ticket.get("tags", []))
        ]).casefold()

        if any(term in searchable_text for term in search_terms):
            matches.append(ticket)

    return {
        "found": len(matches) > 0,
        "query": original_keyword,
        "resolved_service": service["service_id"] if service else None,
        "count": len(matches),
        "tickets": matches
    }
