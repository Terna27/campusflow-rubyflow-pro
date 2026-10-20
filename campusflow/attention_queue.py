from datetime import datetime, timezone
from campusflow.sla import is_overdue


def get_sla_attention_queue(tickets, now=None):
    if now is None:
        now = datetime.now(timezone.utc)

    active_tickets = []

    for ticket in tickets:
        if ticket["status"] in ("open", "in_progress"):
            active_tickets.append(ticket)

    def sort_key(ticket):
        due_at = ticket.get("due_at")

        if not due_at:
            return (
                2,
                datetime.max.replace(tzinfo=timezone.utc),
                int(ticket["id"][1:])
            )

        overdue = is_overdue(ticket, now)

        return (
            0 if overdue else 1,
            datetime.fromisoformat(due_at.replace("Z", "+00:00")),
            int(ticket["id"][1:])
        )

    return sorted(active_tickets, key=sort_key)


def display_sla_attention_queue(tickets, now=None):
    if now is None:
        now = datetime.now(timezone.utc)

    queue = get_sla_attention_queue(tickets, now)

    print("\n========== SLA ATTENTION QUEUE ==========")

    if not queue:
        print("No unresolved tickets found.")
        return

    for ticket in queue:
        due_at = ticket.get("due_at")

        if not due_at:
            label = "NO SLA DEADLINE"
        else:
            overdue = is_overdue(ticket, now)
            label = "OVERDUE" if overdue else "ON TIME"

        print(
            f"ID: {ticket['id']} | "
            f"Title: {ticket['title']} | "
            f"Priority: {ticket['priority']} | "
            f"Status: {ticket['status']} | "
            f"Due: {ticket.get('due_at', 'Not available')} | "
            f"SLA: {label}"
        )