"""Automated unit tests for CampusFlow JSON persistence."""

import os
import tempfile
import unittest
from campusflow.storage import load_tickets, save_tickets
from campusflow.tickets import generate_ticket_id


class TestStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = os.path.join(self.temp_dir.name, "tickets.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_missing_file_returns_empty_list(self):
        """Loading a non-existent file returns an empty list, allowing a fresh start."""
        self.assertFalse(os.path.exists(self.data_path))
        tickets = load_tickets(self.data_path)
        self.assertEqual(tickets, [])

    def test_save_and_load_round_trip(self):
        """Tickets saved to JSON can be reloaded with all fields preserved."""
        original_tickets = [
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
                "title": "Projector broken",
                "category": "Hardware",
                "urgency": "medium",
                "affected_users": 3,
                "priority": "medium",
                "status": "in_progress",
                "assigned_to": "Alice",
            },
        ]

        save_tickets(original_tickets, self.data_path)
        self.assertTrue(os.path.exists(self.data_path))

        loaded_tickets = load_tickets(self.data_path)
        self.assertEqual(loaded_tickets, original_tickets)

    def test_load_malformed_json_raises_value_error(self):
        """Malformed JSON raises ValueError and is never silently erased or replaced."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write("{\ninvalid json data: [not valid")

        with self.assertRaises(ValueError) as ctx:
            load_tickets(self.data_path)
        self.assertIn("Corrupted JSON", str(ctx.exception))

    def test_load_non_list_json_raises_value_error(self):
        """JSON file with root dict or string instead of list raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('{"error": "not a list"}')

        with self.assertRaises(ValueError) as ctx:
            load_tickets(self.data_path)
        self.assertIn("root JSON structure must be a list", str(ctx.exception))

    def test_load_corrupted_ticket_element_raises_value_error(self):
        """List containing non-dict elements raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('[{"id": "T001"}, "not a dict"]')

        with self.assertRaises(ValueError) as ctx:
            load_tickets(self.data_path)
        self.assertIn("not a valid ticket dictionary", str(ctx.exception))

    def test_save_creates_parent_directories_if_needed(self):
        """Saving to a nested path creates missing parent directories automatically."""
        nested_path = os.path.join(self.temp_dir.name, "sub", "deep", "tickets.json")
        tickets = [{"id": "T001", "title": "Test"}]
        save_tickets(tickets, nested_path)
        self.assertTrue(os.path.exists(nested_path))
        loaded = load_tickets(nested_path)
        self.assertEqual(loaded, tickets)

    def test_unique_sequential_id_generation_after_reload(self):
        """Reloaded tickets preserve the highest existing ID to maintain sequential IDs."""
        initial_tickets = [
            {"id": "T001", "title": "First ticket"},
            {"id": "T002", "title": "Second ticket"},
            {"id": "T005", "title": "Fifth ticket"},
        ]
        save_tickets(initial_tickets, self.data_path)

        reloaded_tickets = load_tickets(self.data_path)
        next_id = generate_ticket_id(reloaded_tickets)
        self.assertEqual(next_id, "T006")


if __name__ == "__main__":
    unittest.main()
