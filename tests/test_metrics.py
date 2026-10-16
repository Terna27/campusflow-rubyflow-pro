import unittest
from copy import deepcopy
from datetime import datetime, timezone

from campusflow.metrics import get_enhanced_metrics


class TestEnhancedMetrics(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)

    def make_ticket(self, ticket_id, status, priority, due_at=None, cycle=0):
        return {
            "id": ticket_id,
            "status": status,
            "priority": priority,
            "due_at": due_at,
            "escalation_cycle": cycle
        }

    def test_empty_tickets(self):
        result = get_enhanced_metrics([], now=self.now)

        self.assertEqual(result["open"], 0)
        self.assertEqual(result["in_progress"], 0)
        self.assertEqual(result["resolved"], 0)
        self.assertEqual(result["overdue"], 0)
        self.assertEqual(result["escalated"], 0)

    def test_open_ticket_count(self):
        tickets = [
            self.make_ticket("T001", "open", "high"),
            self.make_ticket("T002", "open", "low")
        ]

        result = get_enhanced_metrics(tickets, now=self.now)

        self.assertEqual(result["open"], 2)

    def test_in_progress_ticket_count(self):
        tickets = [
            self.make_ticket("T001", "in_progress", "high")
        ]

        result = get_enhanced_metrics(tickets, now=self.now)

        self.assertEqual(result["in_progress"], 1)

    def test_resolved_ticket_count(self):
        tickets = [
            self.make_ticket("T001", "resolved", "medium")
        ]

        result = get_enhanced_metrics(tickets, now=self.now)

        self.assertEqual(result["resolved"], 1)

    def test_overdue_unresolved_tickets(self):
        tickets = [
            self.make_ticket("T001", "open", "high", "2026-10-15T10:00:00Z"),
            self.make_ticket("T002", "in_progress", "low", "2026-10-15T10:00:00Z"),
            self.make_ticket("T003", "resolved", "high", "2026-10-15T10:00:00Z")
        ]

        result = get_enhanced_metrics(tickets, now=self.now)

        self.assertEqual(result["overdue"], 2)

    def test_priority_counts(self):
        tickets = [
            self.make_ticket("T001", "open", "critical"),
            self.make_ticket("T002", "open", "high"),
            self.make_ticket("T003", "resolved", "medium"),
            self.make_ticket("T004", "open", "low")
        ]

        result = get_enhanced_metrics(tickets, now=self.now)

        self.assertEqual(result["priority_counts"]["critical"], 1)
        self.assertEqual(result["priority_counts"]["high"], 1)
        self.assertEqual(result["priority_counts"]["medium"], 1)
        self.assertEqual(result["priority_counts"]["low"], 1)

    def test_escalated_in_current_lifecycle(self):
        tickets = [
            self.make_ticket("T001", "open", "high", cycle=1),
            self.make_ticket("T002", "open", "low", cycle=0),
            self.make_ticket("T003", "resolved", "medium", cycle=2)
        ]

        events = [
            {
                "ticket_id": "T001",
                "action": "escalate",
                "timestamp": "2026-10-15T10:00:00Z"
            },
            {
                "ticket_id": "T003",
                "action": "escalate",
                "timestamp": "2026-10-15T11:00:00Z"
            }
        ]

        result = get_enhanced_metrics(tickets, events, now=self.now)

        self.assertEqual(result["escalated"], 2)

    def test_escalation_before_reopening_is_not_counted(self):
        tickets = [
            self.make_ticket("T001", "open", "high", cycle=1)
        ]

        events = [
            {
                "ticket_id": "T001",
                "action": "escalate",
                "timestamp": "2026-10-15T10:00:00Z"
            },
            {
                "ticket_id": "T001",
                "action": "reopen",
                "timestamp": "2026-10-16T09:00:00Z"
            }
        ]

        result = get_enhanced_metrics(tickets, events, now=self.now)

        self.assertEqual(result["escalated"], 0)

    def test_escalation_after_reopening_is_counted(self):
        tickets = [
            self.make_ticket("T001", "open", "high", cycle=2)
        ]

        events = [
            {
                "ticket_id": "T001",
                "action": "escalate",
                "timestamp": "2026-10-14T10:00:00Z"
            },
            {
                "ticket_id": "T001",
                "action": "reopen",
                "timestamp": "2026-10-15T09:00:00Z"
            },
            {
                "ticket_id": "T001",
                "action": "escalate",
                "timestamp": "2026-10-15T12:00:00Z"
            }
        ]

        result = get_enhanced_metrics(tickets, events, now=self.now)

        self.assertEqual(result["escalated"], 1)

    def test_metrics_do_not_modify_tickets(self):
        tickets = [
            self.make_ticket("T001", "open", "high", "2026-10-15T10:00:00Z")
        ]

        events = [
            {
                "ticket_id": "T001",
                "action": "escalate",
                "timestamp": "2026-10-15T11:00:00Z"
            }
        ]

        original_tickets = deepcopy(tickets)
        original_events = deepcopy(events)

        get_enhanced_metrics(tickets, events, now=self.now)

        self.assertEqual(tickets, original_tickets)
        self.assertEqual(events, original_events)


if __name__ == "__main__":
    unittest.main()