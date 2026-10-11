"""Automated unit tests for CampusFlow ticket assignment, workflow, and work queue."""

import unittest
from campusflow.workflow import (
    assign_ticket,
    update_status,
    reopen_ticket,
    get_work_queue,
)


class TestTicketWorkflow(unittest.TestCase):

    def setUp(self):
        """Set up fresh sample tickets before each test."""
        self.tickets = [
            {
                "id": "T001",
                "title": "Wi-Fi outage in library",
                "category": "Network",
                "urgency": "high",
                "affected_users": 20,
                "priority": "critical",
                "status": "open",
                "assigned_to": None,
            },
            {
                "id": "T002",
                "title": "Projector broken in Hall B",
                "category": "Hardware",
                "urgency": "medium",
                "affected_users": 5,
                "priority": "medium",
                "status": "open",
                "assigned_to": "Alice Smith",
            },
            {
                "id": "T003",
                "title": "Software license expired",
                "category": "Software",
                "urgency": "high",
                "affected_users": 1,
                "priority": "high",
                "status": "in_progress",
                "assigned_to": "Bob Jones",
            },
            {
                "id": "T004",
                "title": "Password reset needed",
                "category": "Other",
                "urgency": "low",
                "affected_users": 1,
                "priority": "low",
                "status": "resolved",
                "assigned_to": "Charlie Brown",
            },
        ]

    # --- Feature F3: Assignment Tests ---

    def test_assign_ticket_success(self):
        """Valid staff name assigns ticket and returns updated dictionary."""
        updated = assign_ticket(self.tickets, "T001", "Dr. Jane Doe")
        self.assertEqual(updated["assigned_to"], "Dr. Jane Doe")
        self.assertEqual(self.tickets[0]["assigned_to"], "Dr. Jane Doe")

    def test_assign_ticket_trims_whitespace(self):
        """Staff name with leading/trailing whitespace is properly trimmed."""
        updated = assign_ticket(self.tickets, "T001", "   Jane Doe   ")
        self.assertEqual(updated["assigned_to"], "Jane Doe")

    def test_assign_ticket_rejects_empty_or_whitespace_name(self):
        """Whitespace-only or empty names raise ValueError without mutating ticket."""
        initial_assigned = self.tickets[0]["assigned_to"]
        for empty_val in ["", "   ", "\t\n"]:
            with self.assertRaises(ValueError):
                assign_ticket(self.tickets, "T001", empty_val)
            self.assertEqual(self.tickets[0]["assigned_to"], initial_assigned)

    def test_assign_ticket_unknown_id(self):
        """Unknown ticket ID raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            assign_ticket(self.tickets, "T999", "Technician Mark")
        self.assertIn("T999", str(ctx.exception))

    def test_assign_ticket_rejects_resolved_ticket(self):
        """Resolved tickets cannot be assigned without reopening first."""
        initial_assigned = self.tickets[3]["assigned_to"]
        with self.assertRaises(ValueError) as ctx:
            assign_ticket(self.tickets, "T004", "New Technician")
        self.assertIn("reopen", str(ctx.exception).lower())
        self.assertEqual(self.tickets[3]["assigned_to"], initial_assigned)

    # --- Feature F4: Workflow & Status Transition Tests ---

    def test_transition_open_to_in_progress_when_assigned(self):
        """Open ticket with assigned staff can transition to in_progress."""
        updated = update_status(self.tickets, "T002", "in_progress")
        self.assertEqual(updated["status"], "in_progress")

    def test_transition_open_to_in_progress_normalizes_casing_and_spacing(self):
        """Status input is normalized (case insensitive, trimmed)."""
        updated = update_status(self.tickets, "T002", "  IN_PROGRESS  ")
        self.assertEqual(updated["status"], "in_progress")

    def test_reject_open_to_in_progress_when_unassigned(self):
        """Open ticket without assigned staff cannot transition to in_progress."""
        self.assertIsNone(self.tickets[0]["assigned_to"])
        with self.assertRaises(ValueError) as ctx:
            update_status(self.tickets, "T001", "in_progress")
        self.assertIn("assigned", str(ctx.exception).lower())
        self.assertEqual(self.tickets[0]["status"], "open")

    def test_transition_in_progress_to_resolved(self):
        """In-progress ticket can transition directly to resolved."""
        updated = update_status(self.tickets, "T003", "resolved")
        self.assertEqual(updated["status"], "resolved")

    def test_reject_direct_open_to_resolved(self):
        """Open ticket cannot transition directly to resolved."""
        with self.assertRaises(ValueError) as ctx:
            update_status(self.tickets, "T002", "resolved")
        self.assertIn("in_progress", str(ctx.exception).lower())
        self.assertEqual(self.tickets[1]["status"], "open")

    def test_reject_modifying_resolved_ticket_through_update_status(self):
        """Resolved tickets cannot be modified through normal status transitions."""
        for target in ["open", "in_progress", "resolved"]:
            with self.assertRaises(ValueError):
                update_status(self.tickets, "T004", target)
        self.assertEqual(self.tickets[3]["status"], "resolved")

    def test_reject_unknown_status(self):
        """Unrecognized status value raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            update_status(self.tickets, "T002", "pending_review")
        self.assertIn("invalid status", str(ctx.exception).lower())

    def test_reject_same_status_transition(self):
        """Transitioning to the current status raises ValueError."""
        with self.assertRaises(ValueError):
            update_status(self.tickets, "T002", "open")

    def test_reopen_ticket_success(self):
        """Resolved ticket can be explicitly reopened to open."""
        self.assertEqual(self.tickets[3]["status"], "resolved")
        reopened = reopen_ticket(self.tickets, "T004")
        self.assertEqual(reopened["status"], "open")
        self.assertEqual(self.tickets[3]["status"], "open")

    def test_reopen_ticket_allows_subsequent_workflow_progression(self):
        """A reopened ticket can follow the normal lifecycle again."""
        reopen_ticket(self.tickets, "T004")
        self.assertEqual(self.tickets[3]["status"], "open")
        self.assertEqual(self.tickets[3]["assigned_to"], "Charlie Brown")

        # Now can move to in_progress because it has assigned staff
        update_status(self.tickets, "T004", "in_progress")
        self.assertEqual(self.tickets[3]["status"], "in_progress")

        # Now can move to resolved
        update_status(self.tickets, "T004", "resolved")
        self.assertEqual(self.tickets[3]["status"], "resolved")

    def test_reopen_ticket_rejects_non_resolved_tickets(self):
        """Reopening an open or in_progress ticket raises ValueError."""
        with self.assertRaises(ValueError) as ctx1:
            reopen_ticket(self.tickets, "T001")
        self.assertIn("resolved", str(ctx1.exception).lower())

        with self.assertRaises(ValueError) as ctx2:
            reopen_ticket(self.tickets, "T003")
        self.assertIn("resolved", str(ctx2.exception).lower())

    # --- Feature F5: Work Queue Tests ---

    def test_work_queue_excludes_resolved_tickets(self):
        """Resolved tickets are excluded from the work queue."""
        queue = get_work_queue(self.tickets)
        queue_ids = [t["id"] for t in queue]
        self.assertNotIn("T004", queue_ids)
        self.assertEqual(len(queue), 3)

    def test_work_queue_order_by_priority(self):
        """Work queue orders by critical -> high -> medium -> low."""
        tickets = [
            {"id": "T001", "priority": "low", "status": "open"},
            {"id": "T002", "priority": "critical", "status": "open"},
            {"id": "T003", "priority": "medium", "status": "open"},
            {"id": "T004", "priority": "high", "status": "in_progress"},
        ]
        queue = get_work_queue(tickets)
        order = [t["priority"] for t in queue]
        self.assertEqual(order, ["critical", "high", "medium", "low"])
        self.assertEqual([t["id"] for t in queue], ["T002", "T004", "T003", "T001"])

    def test_work_queue_numeric_id_tie_breaking(self):
        """Equal priority tickets break ties using numeric ID ascending (T002 before T010)."""
        tickets = [
            {"id": "T010", "priority": "high", "status": "open"},
            {"id": "T002", "priority": "high", "status": "open"},
            {"id": "T001", "priority": "high", "status": "in_progress"},
            {"id": "T100", "priority": "high", "status": "open"},
            {"id": "T020", "priority": "high", "status": "open"},
        ]
        queue = get_work_queue(tickets)
        queue_ids = [t["id"] for t in queue]
        self.assertEqual(queue_ids, ["T001", "T002", "T010", "T020", "T100"])

    def test_work_queue_returns_new_list_without_mutating_original(self):
        """Calling get_work_queue does not alter the original list order."""
        original_copy = list(self.tickets)
        queue = get_work_queue(self.tickets)
        self.assertIsNot(queue, self.tickets)
        self.assertEqual(self.tickets, original_copy)

    def test_work_queue_empty_collection(self):
        """Empty input collection returns an empty list without error."""
        self.assertEqual(get_work_queue([]), [])

    def test_work_queue_rejects_unexpected_priority(self):
        """Tickets with unexpected priority values raise ValueError."""
        corrupt_tickets = [
            {"id": "T001", "priority": "super_urgent", "status": "open"}
        ]
        with self.assertRaises(ValueError) as ctx:
            get_work_queue(corrupt_tickets)
        self.assertIn("super_urgent", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
