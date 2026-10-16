"""Ticket creation, sequential ID generation, and validation for CampusFlow."""

from typing import Union
from datetime import datetime

try:
    from campusflow.priority import calculate_priority
except ImportError:
    from priority import calculate_priority

from campusflow.time_utils import (
    UTCTimestamp,
    format_utc_iso,
    resolve_now,
    parse_utc_iso,
)
from campusflow.sla import (
    calculate_due_at,
    is_overdue,
    escalate_overdue,
    SLA_DURATIONS_MINUTES,
)
from campusflow.events import generate_event_id, record_event


def _extract_numeric_ticket_id(ticket_id: str) -> int:
    """Extract numeric suffix from ticket ID (e.g. 'T002' -> 2)."""
    digits = "".join(ch for ch in str(ticket_id) if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid ticket ID format with no numeric component: '{ticket_id}'")
    return int(digits)


def generate_ticket_id(records: list[dict]) -> str:
    """Generate the next sequential ticket identifier (e.g. T001, T002).

    Rules:
        - If records is empty, returns 'T001'.
        - Finds the maximum numeric suffix among existing tickets and increments by 1.
        - Preserves sequential continuity across reloads.
    """
    if not isinstance(records, list):
        raise TypeError("Records collection must be a list")

    if not records:
        return "T001"

    numbers = []
    for record in records:
        if isinstance(record, dict) and "id" in record:
            try:
                numbers.append(_extract_numeric_ticket_id(record["id"]))
            except ValueError:
                continue

    if not numbers:
        return "T001"

    max_id = max(numbers)
    return f"T{max_id + 1:03d}"


def create_ticket(
    title: str,
    category: str,
    urgency: str,
    affected_users: int,
    records: list[dict] | None = None,
    now: Union[datetime, str, None] = None,
) -> dict:
    """Collect ticket details, validate inputs, calculate priority & SLA due date, and create ticket.

    Validations:
        - Title must not be blank after trimming.
        - Category must be one of: Network, Hardware, Software, Other (normalized title-case).
        - Urgency must be one of: low, medium, high (normalized lower-case).
        - Affected users must be a positive integer (>= 1, not boolean, not string).
        - Created/updated timestamps are stored in UTC ISO-8601 format.
        - due_at is calculated based on priority SLA duration.
        - escalation_cycle starts at 0.

    Returns:
        Ticket dictionary with all canonical and SLA fields.
    """
    if not isinstance(title, str):
        raise ValueError("Title must be a string")

    title_clean = title.strip()
    if title_clean == "":
        raise ValueError("Empty Text")

    if not isinstance(category, str):
        raise ValueError("Category must be a string")

    categories = ("Network", "Hardware", "Software", "Other")
    category_normalized = category.strip().title()
    if category_normalized not in categories:
        raise ValueError("Supplied Category is invalid")

    if not isinstance(urgency, str):
        raise ValueError("Urgency must be a string")

    urgencies = ("low", "medium", "high")
    urgency_normalized = urgency.strip().lower()
    if urgency_normalized not in urgencies:
        raise ValueError("Urgencies level does not exist")

    if not isinstance(affected_users, int) or isinstance(affected_users, bool) or affected_users < 1:
        raise ValueError("Incorrect input; user must be atleast 1 written in number")

    priority = calculate_priority(urgency_normalized, affected_users)
    ticket_id = generate_ticket_id(records) if records is not None else "T001"

    # Deterministic UTC time handling
    now_dt = resolve_now(now)
    now_iso = format_utc_iso(now_dt)
    due_at = calculate_due_at(priority, cycle_start=now_dt)

    my_ticket = {
        "id": ticket_id,
        "title": title_clean,
        "category": category_normalized,
        "urgency": urgency_normalized,
        "affected_users": affected_users,
        "priority": priority,
        "status": "open",
        "assigned_to": None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "due_at": due_at,
        "escalation_cycle": 0,
    }
    return my_ticket
