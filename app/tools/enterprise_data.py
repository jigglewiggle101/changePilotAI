"""Read-only tools over the synthetic ChangePilot dataset."""
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

def load_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_service(service_id: str) -> dict[str, Any] | None:
    """Return one service by exact ID or exact name."""
    services = load_json("services.json")
    query = service_id.strip().casefold()

    return next(
        (
            s for s in services
            if s["service_id"].casefold() == query
            or s["name"].strip().casefold() == query
        ),
        None
    )


def get_service_dependencies(service_id: str) -> dict[str, Any]:
    """Return direct dependency details by service ID or exact name."""
    service = get_service(service_id)

    if not service:
        return {
            "found": False,
            "service_id": service_id,
            "dependencies": []
        }

    dependencies = [
        get_service(dep_id)
        for dep_id in service.get("depends_on", [])
    ]

    return {
        "found": True,
        "service": service,
        "dependencies": [d for d in dependencies if d is not None]
    }


def get_dependent_services(service_id: str) -> dict[str, Any]:
    """Find services that directly depend on the specified service."""
    service = get_service(service_id)

    if not service:
        return {
            "found": False,
            "service_id": service_id,
            "dependents": []
        }

    all_services = load_json("services.json")

    dependents = [
        s for s in all_services
        if service["service_id"] in s.get("depends_on", [])
    ]

    return {
        "found": True,
        "service": service,
        "dependents": dependents
    }


def get_transitive_dependencies(service_id: str) -> dict[str, Any]:
    """Recursively return all downstream dependencies of a service."""
    service = get_service(service_id)

    if not service:
        return {
            "found": False,
            "service_id": service_id,
            "dependencies": []
        }

    all_services = load_json("services.json")
    services_by_id = {
        s["service_id"]: s for s in all_services
    }

    visited = set()
    dependencies = []

    def traverse(current_service):
        for dep_id in current_service.get("depends_on", []):
            if dep_id in visited:
                continue

            visited.add(dep_id)

            dependency = services_by_id.get(dep_id)

            if dependency is None:
                continue

            dependencies.append(dependency)
            traverse(dependency)

    traverse(service)

    return {
        "found": True,
        "service": service,
        "dependencies": dependencies
    }


def get_transitive_dependents(service_id: str) -> dict[str, Any]:
    """
    Find all direct and indirect dependents of a service.
    Preserve multiple dependency paths without duplicating services.
    """
    service = get_service(service_id)

    if not service:
        return {
            "found": False,
            "service_id": service_id,
            "dependents": [],
            "relationship_details": []
        }

    all_services = load_json("services.json")
    relationships = {}

    def traverse(target_id: str, current_path: list[str]):
        for candidate in all_services:
            candidate_id = candidate["service_id"]

            if target_id not in candidate.get("depends_on", []):
                continue

            # Prevent cycles in the current path.
            if candidate_id in current_path:
                continue

            new_path = current_path + [candidate_id]

            relationships.setdefault(candidate_id, []).append(new_path)

            traverse(candidate_id, new_path)

    traverse(service["service_id"], [service["service_id"]])

    services_by_id = {
        s["service_id"]: s for s in all_services
    }

    dependents = [
        services_by_id[dependent_id]
        for dependent_id in relationships
    ]

    relationship_details = []

    for dependent_id, paths in relationships.items():
        relationship_details.append({
            "service": services_by_id[dependent_id],
            "is_direct": any(len(path) == 2 for path in paths),
            "indirect_paths": [
                path for path in paths if len(path) > 2
            ]
        })

    return {
        "found": True,
        "service": service,
        "dependents": dependents,
        "relationship_details": relationship_details
    }

def search_services(keyword: str) -> list[dict[str, Any]]:
    if not isinstance(keyword, str) or not keyword.strip() or len(keyword) > 100:
        raise ValueError("keyword must be a non-empty string of at most 100 characters")
    q = keyword.casefold()
    return [
        s for s in load_json("services.json")
        if q in s["name"].casefold() or q in s["description"].casefold()
    ]