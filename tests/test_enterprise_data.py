
from app.tools.enterprise_data import (
    get_service,
    get_service_dependencies
)

from app.tools.ticket_search import search_change_tickets
from app.tools.enterprise_data import get_transitive_dependents


def test_known_service_exists():
    assert get_service("SVC-110")["name"] == "Employee Access Service"


def test_unknown_service_returns_not_found():
    assert get_service_dependencies("SVC-999")["found"] is False


def test_dependency_tool_returns_direct_dependency():
    result = get_service_dependencies("SVC-100")

    assert result["found"] is True

    assert {
        s["service_id"] for s in result["dependencies"]
    } == {"SVC-110", "SVC-120"}


def test_ticket_search_finds_identity_incident():
    result = search_change_tickets("identity")

    assert result["found"] is True

    assert any(
        ticket["ticket_id"] == "INC-003"
        for ticket in result["tickets"]
    )


def test_ticket_search_rejects_empty_query():
    result = search_change_tickets("")

    assert result["found"] is False
    assert result["count"] == 0
    assert result["tickets"] == []
    assert result["message"] == "Please provide a valid search keyword."


def test_transitive_dependents_identifies_multiple_paths():
    result = get_transitive_dependents("SVC-100")

    assert result["found"] is True

    details = {
        item["service"]["service_id"]: item
        for item in result["relationship_details"]
    }

    # SVC-130 and SVC-610 are direct dependents.
    assert details["SVC-130"]["is_direct"] is True
    assert details["SVC-610"]["is_direct"] is True

    # SVC-410 has both direct and indirect paths.
    assert details["SVC-410"]["is_direct"] is True
    assert len(details["SVC-410"]["indirect_paths"]) >= 1

    # Each dependent should appear only once.
    dependent_ids = [
        service["service_id"]
        for service in result["dependents"]
    ]

    assert len(dependent_ids) == len(set(dependent_ids))