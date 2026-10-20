from datetime import datetime, timezone
from campusflow.time_utils import parse_utc_iso
from campusflow.sla import is_overdue


def get_enhanced_metrics(tickets, events=None, now=None):
    if now is None:
        now = datetime.now(timezone.utc)

    metrics = {
        "open": 0,
        "in_progress": 0,
        "resolved": 0,
        "overdue": 0,
        "escalated": 0,
        "priority_counts": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }

    for ticket in tickets:
        status = ticket["status"]
        priority = ticket["priority"]

        if status in ("open", "in_progress", "resolved"):
            metrics[status] += 1

        if priority in metrics["priority_counts"]:
            metrics["priority_counts"][priority] += 1

        if status in ("open", "in_progress"):
            if ticket.get("due_at") and is_overdue(ticket, now):
                metrics["overdue"] += 1

        ticket_events = [
            event for event in (events or [])
            if event.get("ticket_id") == ticket.get("id")
        ]

        reopen_times = [
            parse_utc_iso(event["timestamp"])
            for event in ticket_events
            if event.get("action") == "reopen"
        ]

        latest_reopen = max(reopen_times, default=None)

        escalated_in_current_lifecycle = any(
            event.get("action") == "escalate"
            and (
                latest_reopen is None
                or parse_utc_iso(event["timestamp"]) > latest_reopen
            )
            for event in ticket_events
        )

        if escalated_in_current_lifecycle:
            metrics["escalated"] += 1

    return metrics


def display_enhanced_metrics(tickets, events=None, now=None):
    metrics = get_enhanced_metrics(tickets, events, now)

    print("\n========== ENHANCED METRICS ==========")
    print(f"Open Tickets: {metrics['open']}")
    print(f"In Progress Tickets: {metrics['in_progress']}")
    print(f"Resolved Tickets: {metrics['resolved']}")
    print(f"Overdue Unresolved Tickets: {metrics['overdue']}")
    print(f"Tickets Escalated in Current Lifecycle: {metrics['escalated']}")

    print("\nTickets by Priority:")

    for priority, count in metrics["priority_counts"].items():
        print(f"{priority.capitalize()}: {count}")