"""SLA calculation, overdue detection, and escalation for CampusFlow tickets."""

from datetime import datetime, timedelta
from typing import Union

from campusflow.time_utils import (
    UTCTimestamp,
    parse_utc_iso,
    format_utc_iso,
    resolve_now,
)
from campusflow.events import record_event

# SLA Durations in minutes per priority level
SLA_DURATIONS_MINUTES = {
    "critical": 60,       # 1 hour
    "high": 240,          # 4 hours
    "medium": 1440,       # 24 hours (1 day)
    "low": 2880,          # 48 hours (2 days)
}

ALLOWED_PRIORITIES = set(SLA_DURATIONS_MINUTES.keys())


def calculate_due_at(
    priority: Union[str, dict],
    cycle_start: Union[datetime, str, None] = None,
) -> UTCTimestamp:
    """Calculate the SLA deadline (due_at) from cycle_start based on priority SLA duration.

    Args:
        priority: Priority level string ('critical', 'high', 'medium', 'low')
                  OR a ticket dictionary containing a 'priority' key.
        cycle_start: Timezone-aware datetime or ISO-8601 string representing cycle start.
                     If priority is a ticket dictionary and cycle_start is None,
                     uses ticket's 'updated_at' or 'created_at'.

    SLA Durations:
        - critical: 60 minutes
        - high:     240 minutes
        - medium:   1440 minutes
        - low:      2880 minutes

    Returns:
        UTCTimestamp: ISO-8601 UTC string that compares equal to matching datetime objects.

    Raises:
        ValueError: If priority is unrecognized, cycle_start is missing/invalid,
                    or timestamp is naive.
    """
    # Support passing ticket dictionary as first argument
    if isinstance(priority, dict):
        ticket = priority
        actual_priority = ticket.get("priority")
        if cycle_start is None:
            cycle_start = ticket.get("updated_at") or ticket.get("created_at")
        priority = actual_priority

    if not isinstance(priority, str):
        raise ValueError(f"Priority must be a string, received {type(priority).__name__}")

    normalized_priority = priority.strip().lower()
    if normalized_priority not in SLA_DURATIONS_MINUTES:
        raise ValueError(
            f"Invalid priority '{priority}'. Allowed priorities are: {', '.join(sorted(ALLOWED_PRIORITIES))}"
        )

    if cycle_start is None:
        raise ValueError("cycle_start is required to calculate due_at.")

    start_dt = parse_utc_iso(cycle_start)
    duration_minutes = SLA_DURATIONS_MINUTES[normalized_priority]
    due_dt = start_dt + timedelta(minutes=duration_minutes)

    return format_utc_iso(due_dt)


def is_overdue(ticket: dict, now: Union[datetime, str, None] = None) -> bool:
    """Check whether an active ticket has exceeded its SLA deadline.

    Rules:
        - A resolved ticket is never overdue.
        - An active (open, in_progress) ticket is overdue if now > due_at.
        - If ticket has no due_at timestamp, returns False.
        - Resolves injected or default UTC clock once.
        - Rejects naive now or invalid ticket formats.

    Returns:
        bool: True if ticket is active and overdue, False otherwise.
    """
    if not isinstance(ticket, dict):
        raise TypeError(f"Ticket must be a dictionary, received {type(ticket).__name__}")

    # Resolved tickets cannot be overdue
    status = str(ticket.get("status", "")).strip().lower()
    if status == "resolved":
        return False

    due_at = ticket.get("due_at")
    if due_at is None:
        return False

    due_dt = parse_utc_iso(due_at)
    now_dt = resolve_now(now)

    return now_dt > due_dt


def escalate_overdue(
    tickets: list[dict],
    events: list[dict],
    now: Union[datetime, str, None] = None,
    actor: str = "system",
) -> list[dict]:
    """Escalate all overdue active tickets and record escalation events.

    For each overdue ticket:
        1. Increments escalation_cycle (initially 0 -> 1, etc.).
        2. Sets updated_at to now.
        3. Recalculates due_at from now based on SLA for ticket's priority.
        4. Appends an escalation event to the events list.

    Args:
        tickets: List of ticket dictionaries.
        events: List of event dictionaries (modified in place).
        now: Optional injected UTC timestamp. Default UTC clock resolved ONCE.
        actor: Identifier of entity triggering escalation (default: 'system').

    Returns:
        List of tickets that were escalated during this run.
    """
    if not isinstance(tickets, list):
        raise TypeError("Tickets collection must be a list")
    if not isinstance(events, list):
        raise TypeError("Events collection must be a list")

    # Resolve default UTC clock ONCE per operation
    now_dt = resolve_now(now)
    now_iso = format_utc_iso(now_dt)

    escalated_tickets = []

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue

        if is_overdue(ticket, now=now_dt):
            # Increment escalation cycle
            current_cycle = ticket.get("escalation_cycle", 0)
            if not isinstance(current_cycle, int) or isinstance(current_cycle, bool):
                current_cycle = 0
            new_cycle = current_cycle + 1
            ticket["escalation_cycle"] = new_cycle

            # Update timestamps
            ticket["updated_at"] = now_iso
            ticket["due_at"] = calculate_due_at(ticket["priority"], cycle_start=now_dt)

            # Record escalation event in shared event history
            record_event(
                events=events,
                ticket_id=ticket.get("id", "UNKNOWN"),
                action="escalate",
                actor=actor,
                timestamp=now_iso,
                details={
                    "escalation_cycle": new_cycle,
                    "priority": ticket.get("priority"),
                    "new_due_at": str(ticket["due_at"]),
                },
            )

            escalated_tickets.append(ticket)

    return escalated_tickets
