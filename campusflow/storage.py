"""JSON persistence for CampusFlow tickets and events with Version-2 schema, defensive validation, and atomic replacement."""

import json
import os
import tempfile
from typing import Union

from campusflow.time_utils import parse_utc_iso
from campusflow.events import validate_event

DEFAULT_DATA_PATH = os.path.join("data", "tickets.json")

VALID_CATEGORIES = {"Network", "Hardware", "Software", "Other"}
VALID_URGENCIES = {"low", "medium", "high"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_STATUSES = {"open", "in_progress", "resolved"}


def validate_ticket_record(ticket: dict, index: int | None = None) -> None:
    """Defensively validate an individual ticket dictionary.

    Raises:
        ValueError: If ticket structure or field types/values are invalid.
    """
    prefix = f"Ticket at index {index}: " if index is not None else "Ticket: "

    if not isinstance(ticket, dict):
        raise ValueError(f"{prefix}must be a dictionary, found {type(ticket).__name__}")

    # Required fields
    required_fields = ["id", "title", "category", "urgency", "affected_users", "priority", "status"]
    for field in required_fields:
        if field not in ticket:
            raise ValueError(f"{prefix}missing required field '{field}'")

    # ID validation
    tid = ticket["id"]
    if not isinstance(tid, str) or not tid.strip():
        raise ValueError(f"{prefix}id must be a non-empty string, found {tid!r}")

    # Title validation
    title = ticket["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"{prefix}title must be a non-empty string, found {title!r}")

    # Category validation
    category = ticket["category"]
    if not isinstance(category, str) or category not in VALID_CATEGORIES:
        raise ValueError(f"{prefix}invalid category '{category}'. Allowed: {VALID_CATEGORIES}")

    # Urgency validation
    urgency = ticket["urgency"]
    if not isinstance(urgency, str) or urgency not in VALID_URGENCIES:
        raise ValueError(f"{prefix}invalid urgency '{urgency}'. Allowed: {VALID_URGENCIES}")

    # Affected users validation
    users = ticket["affected_users"]
    if not isinstance(users, int) or isinstance(users, bool) or users < 1:
        raise ValueError(f"{prefix}affected_users must be a positive integer (>= 1), found {users!r}")

    # Priority validation
    priority = ticket["priority"]
    if not isinstance(priority, str) or priority not in VALID_PRIORITIES:
        raise ValueError(f"{prefix}invalid priority '{priority}'. Allowed: {VALID_PRIORITIES}")

    # Status validation
    status = ticket["status"]
    if not isinstance(status, str) or status not in VALID_STATUSES:
        raise ValueError(f"{prefix}invalid status '{status}'. Allowed: {VALID_STATUSES}")

    # Assigned to validation
    assigned = ticket.get("assigned_to")
    if assigned is not None and (not isinstance(assigned, str) or not assigned.strip()):
        raise ValueError(f"{prefix}assigned_to must be None or a non-empty string, found {assigned!r}")

    # Optional timestamp validations
    for ts_field in ("created_at", "updated_at", "due_at"):
        if ts_field in ticket and ticket[ts_field] is not None:
            try:
                parse_utc_iso(ticket[ts_field])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{prefix}field '{ts_field}' has invalid UTC timestamp: {exc}") from exc

    # Escalation cycle validation
    cycle = ticket.get("escalation_cycle")
    if cycle is not None and (not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0):
        raise ValueError(f"{prefix}escalation_cycle must be a non-negative integer, found {cycle!r}")


def _defensively_validate_collection(tickets: list[dict], events: list[dict] | None = None) -> None:
    """Validate tickets and events collections for structural integrity and ID uniqueness."""
    if not isinstance(tickets, list):
        raise TypeError(f"Tickets must be a list, received {type(tickets).__name__}")

    seen_ticket_ids = set()
    for idx, item in enumerate(tickets):
        validate_ticket_record(item, idx)
        tid = item["id"]
        if tid in seen_ticket_ids:
            raise ValueError(f"Duplicate ticket ID '{tid}' detected in tickets collection")
        seen_ticket_ids.add(tid)

    if events is not None:
        if not isinstance(events, list):
            raise TypeError(f"Events must be a list, received {type(events).__name__}")
        seen_event_ids = set()
        for idx, event in enumerate(events):
            validate_event(event)
            eid = event["id"]
            if eid in seen_event_ids:
                raise ValueError(f"Duplicate event ID '{eid}' detected in events collection")
            seen_event_ids.add(eid)


def load_tickets(filepath: str = DEFAULT_DATA_PATH) -> list[dict]:
    """Load tickets from a JSON file, supporting both Version-1 and Version-2 schemas.

    Rules:
        - If file does not exist, returns empty list (permits fresh start).
        - If JSON is malformed, raises ValueError with 'Corrupted JSON'.
        - If root structure is a Version-2 dictionary ({"version": 2, "tickets": [...]}),
          extracts and returns the tickets list.
        - If root structure is a list, returns the validated tickets list.
        - If root is a dict without valid v2 schema or another type, raises ValueError.
        - Never silently replaces corrupted data with an empty list.

    Returns:
        List of ticket dictionaries.
    """
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupted JSON in data file '{filepath}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read data file '{filepath}': {exc}") from exc

    # Version-2 Container
    if isinstance(data, dict):
        if data.get("version") == 2 and "tickets" in data:
            tickets = data["tickets"]
            if not isinstance(tickets, list):
                raise ValueError(
                    f"Corrupted data file '{filepath}': Version 2 'tickets' must be a list, found {type(tickets).__name__}"
                )
            for idx, item in enumerate(tickets):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"Corrupted data file '{filepath}': item at index {idx} is not a valid ticket dictionary"
                    )
            return tickets
        raise ValueError(
            f"Corrupted data file '{filepath}': root JSON structure must be a list of tickets, found {type(data).__name__}"
        )

    # Version-1 Container (root list)
    if not isinstance(data, list):
        raise ValueError(
            f"Corrupted data file '{filepath}': root JSON structure must be a list of tickets, found {type(data).__name__}"
        )

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Corrupted data file '{filepath}': item at index {idx} is not a valid ticket dictionary"
            )

    return data


def load_data(filepath: str = DEFAULT_DATA_PATH) -> tuple[list[dict], list[dict]]:
    """Load both tickets and events from a JSON file with defensive validation.

    Supports:
        - Version-2 JSON format: {"version": 2, "tickets": [...], "events": [...]}
        - Version-1 JSON format: [...] (returns tickets, empty events list)
        - Non-existent file: returns ([], [])

    Returns:
        Tuple of (tickets_list, events_list).

    Raises:
        ValueError: If file is corrupted, invalid JSON, or contains corrupted tickets/events.
    """
    if not os.path.exists(filepath):
        return [], []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupted JSON in data file '{filepath}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read data file '{filepath}': {exc}") from exc

    if isinstance(data, dict):
        if data.get("version") == 2:
            tickets = data.get("tickets")
            events = data.get("events", [])
            _defensively_validate_collection(tickets, events)
            return tickets, events
        raise ValueError(
            f"Corrupted data file '{filepath}': dictionary missing 'version: 2' specification."
        )

    if isinstance(data, list):
        # Version-1 backward compatibility
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Corrupted data file '{filepath}': item at index {idx} is not a valid ticket dictionary"
                )
        return data, []

    raise ValueError(
        f"Corrupted data file '{filepath}': root JSON structure must be a Version-2 dictionary or list, found {type(data).__name__}"
    )


def _atomic_write_json(data: Union[list, dict], filepath: str) -> None:
    """Internal helper to atomically write data to filepath using a temporary file."""
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    target_dir = directory if directory else "."

    temp_file = tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8")
    temp_path = temp_file.name
    try:
        json.dump(data, temp_file, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def save_tickets(tickets: list[dict], filepath: str = DEFAULT_DATA_PATH) -> None:
    """Save tickets to a JSON file using atomic replacement.

    Maintains backward compatibility with Version-1 tests expecting a list root,
    while ensuring directory creation and atomic replacement.
    """
    if not isinstance(tickets, list):
        raise TypeError(f"Tickets must be a list, received {type(tickets).__name__}")

    for idx, item in enumerate(tickets):
        if not isinstance(item, dict):
            raise ValueError(f"All ticket items must be dictionaries, item at index {idx} is {type(item).__name__}")

    _atomic_write_json(tickets, filepath)


def save_data(
    tickets: list[dict],
    events: list[dict] | None = None,
    filepath: str = DEFAULT_DATA_PATH,
) -> None:
    """Save tickets and events in Version-2 format with defensive validation and atomic saving.

    Container format:
        {
            "version": 2,
            "tickets": [...],
            "events": [...]
        }

    Raises:
        TypeError: If tickets or events are not lists.
        ValueError: If any ticket or event fails defensive validation.
    """
    if events is None:
        events = []

    _defensively_validate_collection(tickets, events)

    payload = {
        "version": 2,
        "tickets": tickets,
        "events": events,
    }

    _atomic_write_json(payload, filepath)
