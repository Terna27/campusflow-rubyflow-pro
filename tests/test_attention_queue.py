import unittest
from copy import deepcopy
from datetime import datetime, timezone
from io import StringIO
from contextlib import redirect_stdout

from campusflow.attention_queue import (
    get_sla_attention_queue,
    display_sla_attention_queue,
)


class TestSLAAttentionQueue(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)

    def make_ticket(self, ticket_id, status, due_at):
        return {
            "id": ticket_id,
            "title": "Network issue",
            "priority": "high",
            "status": status,
            "due_at": due_at,
        }

    def test_empty_queue(self):
        result = get_sla_attention_queue([], self.now)
        self.assertEqual(result, [])

    def test_resolved_tickets_are_excluded(self):
        tickets = [
            self.make_ticket("T001", "resolved", "2026-10-15T10:00:00Z"),
            self.make_ticket("T002", "open", "2026-10-17T10:00:00Z"),
        ]

        result = get_sla_attention_queue(tickets, self.now)

        self.assertEqual([t["id"] for t in result], ["T002"])

    def test_overdue_tickets_appear_first(self):
        tickets = [
            self.make_ticket("T001", "open", "2026-10-17T10:00:00Z"),
            self.make_ticket("T002", "in_progress", "2026-10-15T10:00:00Z"),
        ]

        result = get_sla_attention_queue(tickets, self.now)

        self.assertEqual([t["id"] for t in result], ["T002", "T001"])

    def test_tickets_sorted_by_deadline(self):
        tickets = [
            self.make_ticket("T001", "open", "2026-10-18T10:00:00Z"),
            self.make_ticket("T002", "open", "2026-10-17T10:00:00Z"),
        ]

        result = get_sla_attention_queue(tickets, self.now)

        self.assertEqual([t["id"] for t in result], ["T002", "T001"])

    def test_numeric_ticket_id_tie_breaking(self):
        tickets = [
            self.make_ticket("T010", "open", "2026-10-17T10:00:00Z"),
            self.make_ticket("T002", "open", "2026-10-17T10:00:00Z"),
        ]

        result = get_sla_attention_queue(tickets, self.now)

        self.assertEqual([t["id"] for t in result], ["T002", "T010"])

    def test_missing_deadline_appears_last(self):
        tickets = [
            self.make_ticket("T001", "open", None),
            self.make_ticket("T002", "open", "2026-10-17T10:00:00Z"),
        ]

        result = get_sla_attention_queue(tickets, self.now)

        self.assertEqual([t["id"] for t in result], ["T002", "T001"])

    def test_queue_does_not_modify_tickets(self):
        tickets = [
            self.make_ticket("T002", "open", "2026-10-17T10:00:00Z"),
            self.make_ticket("T001", "open", "2026-10-15T10:00:00Z"),
        ]

        original = deepcopy(tickets)

        get_sla_attention_queue(tickets, self.now)

        self.assertEqual(tickets, original)

    def test_display_labels_overdue_tickets(self):
        tickets = [
            self.make_ticket("T001", "open", "2026-10-15T10:00:00Z"),
        ]

        output = StringIO()

        with redirect_stdout(output):
            display_sla_attention_queue(tickets, self.now)

        self.assertIn("OVERDUE", output.getvalue())
        self.assertIn("T001", output.getvalue())