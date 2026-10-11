"""Automated unit tests for ticket creation and validation."""

import unittest
from campusflow.tickets import create_ticket, generate_ticket_id


class TestTicketCreation(unittest.TestCase):

    def test_create_valid_ticket(self):
        """Ticket creation succeeds with valid inputs and calculates priority."""
        ticket = create_ticket(
            title="Projector in Room 101 not working",
            category="Hardware",
            urgency="high",
            affected_users=12,
        )
        self.assertEqual(ticket["title"], "Projector in Room 101 not working")
        self.assertEqual(ticket["category"], "Hardware")
        self.assertEqual(ticket["urgency"], "high")
        self.assertEqual(ticket["affected_users"], 12)
        self.assertEqual(ticket["priority"], "critical")
        self.assertEqual(ticket["status"], "open")
        self.assertIsNone(ticket["assigned_to"])

    def test_create_ticket_rejects_empty_title(self):
        """Empty or whitespace-only title raises ValueError."""
        with self.assertRaises(ValueError):
            create_ticket("   ", "Network", "high", 5)

    def test_create_ticket_rejects_invalid_category(self):
        """Invalid category raises ValueError."""
        with self.assertRaises(ValueError):
            create_ticket("Broken AC", "Facilities", "high", 5)

    def test_create_ticket_rejects_invalid_urgency(self):
        """Invalid urgency level raises ValueError."""
        with self.assertRaises(ValueError):
            create_ticket("Broken mouse", "Hardware", "extreme", 1)

    def test_create_ticket_rejects_invalid_affected_users(self):
        """Affected users must be an integer >= 1."""
        with self.assertRaises(ValueError):
            create_ticket("Broken keyboard", "Hardware", "low", 0)
        with self.assertRaises(ValueError):
            create_ticket("Broken keyboard", "Hardware", "low", -2)
        with self.assertRaises(ValueError):
            create_ticket("Broken keyboard", "Hardware", "low", True)

    def test_generate_ticket_id_sequential(self):
        """Sequential IDs are incremented properly."""
        records = [
            {"id": "T001"},
            {"id": "T002"},
            {"id": "T015"},
        ]
        self.assertEqual(generate_ticket_id(records), "T016")

    def test_generate_ticket_id_empty_records(self):
        """Empty records list starts with T001."""
        self.assertEqual(generate_ticket_id([]), "T001")


if __name__ == "__main__":
    unittest.main()
