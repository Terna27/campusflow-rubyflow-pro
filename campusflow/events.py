"""Event model, sequential ID generation, and history recording contract."""

from typing import Union
from datetime import datetime
from campusflow.time_utils import format_utc_iso, resolve_now, parse_utc_iso


def _extract_numeric_event_id(event_id: str) -> int:
    """Extract numeric suffix from an event ID (e.g. 'E002' -> 2)."""
    digits = "".join(ch for ch in str(event_id) if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid event ID format with no numeric component: '{event_id}'")
    return int(digits)


def generate_event_id(events: list[dict]) -> str:
    """Generate the next sequential event identifier (e.g. E001, E002).

    Rules:
        - If events is empty, returns 'E001'.
        - Finds the maximum numeric suffix among existing events and increments by 1.
        - Preserves sequential continuity across reloads.
    """
    if not isinstance(events, list):
        raise TypeError("Events collection must be a list")

    numbers = []
    for event in events:
        if isinstance(event, dict) and "id" in event:
            try:
                numbers.append(_extract_numeric_event_id(event["id"]))
            except ValueError:
                continue

    if not numbers:
        return "E001"

    max_id = max(numbers)
    return f"E{max_id + 1:03d}"


def validate_event(event: dict) -> None:
    """Defensively validate an individual event dictionary.

    Raises:
        ValueError: If mandatory fields are missing or corrupted.
    """
    if not isinstance(event, dict):
        raise ValueError(f"Event must be a dictionary, found {type(event).__name__}")

    for field in ("id", "ticket_id", "action", "timestamp", "actor"):
        if field not in event or not isinstance(event[field], str) or not event[field].strip():
            raise ValueError(f"Event missing or invalid mandatory field '{field}': {event}")

    # Validate timestamp is valid ISO with explicit timezone
    parse_utc_iso(event["timestamp"])

    # Details must be a dictionary if present
    if "details" in event and not isinstance(event["details"], dict):
        raise ValueError(f"Event 'details' must be a dictionary: {event}")


def record_event(
    events: list[dict],
    ticket_id: str,
    action: str,
    actor: str = "system",
    timestamp: Union[datetime, str, None] = None,
    details: dict | None = None,
) -> dict:
    """Record an audit trail event according to Developer B's shared integration contract.

    Args:
        events: Mutable list of event dictionaries.
        ticket_id: ID of the ticket affected.
        action: Operation identifier (e.g. 'create', 'assign', 'status_change', 'reopen', 'escalate').
        actor: Identity of actor performing the operation.
        timestamp: Optional timestamp (defaults to current UTC time resolved once).
        details: Optional contextual metadata dictionary.

    Returns:
        The newly created and appended event dictionary.
    """
    if not isinstance(events, list):
        raise TypeError("Events collection must be a list")

    now_dt = resolve_now(timestamp)
    now_iso = format_utc_iso(now_dt)

    event_id = generate_event_id(events)
    event = {
        "id": event_id,
        "ticket_id": str(ticket_id),
        "action": str(action).strip(),
        "timestamp": now_iso,
        "actor": str(actor).strip() if actor else "system",
        "details": details if isinstance(details, dict) else {},
    }

    validate_event(event)
    events.append(event)
    return event
