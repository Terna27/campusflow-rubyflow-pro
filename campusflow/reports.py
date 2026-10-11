"""Reporting functionality for CampusFlow tickets."""

ALLOWED_STATUSES = ("open", "in_progress", "resolved")
ALLOWED_PRIORITIES = ("critical", "high", "medium", "low")


def generate_report(tickets: list[dict]) -> dict:
    """Generate aggregate statistics across all tickets.

    Calculates:
        - Total number of tickets
        - Breakdown counts for all allowed statuses (including 0 counts)
        - Breakdown counts for all allowed priorities (including 0 counts)

    Returns:
        A dictionary with keys 'total', 'by_status', and 'by_priority'.
    """
    if not isinstance(tickets, list):
        raise TypeError("Tickets collection must be a list")

    by_status = {status: 0 for status in ALLOWED_STATUSES}
    by_priority = {priority: 0 for priority in ALLOWED_PRIORITIES}

    total = 0
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        total += 1

        status = ticket.get("status")
        if status in by_status:
            by_status[status] += 1

        priority = ticket.get("priority")
        if priority in by_priority:
            by_priority[priority] += 1

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
    }
