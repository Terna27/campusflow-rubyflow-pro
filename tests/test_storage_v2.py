"""Unit tests for Version-2 JSON persistence, defensive validation, and ID continuity."""

import os
import json
import tempfile
import unittest

from campusflow.storage import (
    load_data,
    save_data,
    load_tickets,
    save_tickets,
    validate_ticket_record,
)
from campusflow.tickets import generate_ticket_id
from campusflow.events import generate_event_id, validate_event


class TestStorageV2(unittest.TestCase):
    """Test Version-2 JSON persistence, defensive validation, and schema upgrades."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = os.path.join(self.temp_dir.name, "tickets_v2.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_missing_file_returns_empty_lists(self):
        """Loading a non-existent file returns ([], []) allowing a clean start."""
        tickets, events = load_data(self.data_path)
        self.assertEqual(tickets, [])
        self.assertEqual(events, [])

    def test_save_and_load_round_trip_v2(self):
        """Tickets and events saved with Version-2 schema reload with complete fidelity."""
        tickets = [
            {
                "id": "T001",
                "title": "Wi-Fi outage in library",
                "category": "Network",
                "urgency": "high",
                "affected_users": 20,
                "priority": "critical",
                "status": "open",
                "assigned_to": "Jane",
                "created_at": "2026-10-14T10:00:00Z",
                "updated_at": "2026-10-14T10:00:00Z",
                "due_at": "2026-10-14T11:00:00Z",
                "escalation_cycle": 0,
            }
        ]
        events = [
            {
                "id": "E001",
                "ticket_id": "T001",
                "action": "create",
                "timestamp": "2026-10-14T10:00:00Z",
                "actor": "admin",
                "details": {"priority": "critical"},
            }
        ]

        save_data(tickets, events, self.data_path)
        self.assertTrue(os.path.exists(self.data_path))

        # Inspect raw JSON file to confirm version 2 structure
        with open(self.data_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(raw.get("version"), 2)
        self.assertIn("tickets", raw)
        self.assertIn("events", raw)

        loaded_tickets, loaded_events = load_data(self.data_path)
        self.assertEqual(loaded_tickets, tickets)
        self.assertEqual(loaded_events, events)

    def test_load_data_backward_compatible_with_v1_list(self):
        """load_data correctly loads Version-1 list-only files and returns empty events."""
        v1_data = [
            {
                "id": "T001",
                "title": "Old format ticket",
                "category": "Hardware",
                "urgency": "low",
                "affected_users": 1,
                "priority": "low",
                "status": "open",
                "assigned_to": None,
            }
        ]
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(v1_data, f)

        tickets, events = load_data(self.data_path)
        self.assertEqual(tickets, v1_data)
        self.assertEqual(events, [])

    def test_load_tickets_backward_compatible_with_v2_file(self):
        """load_tickets can read a Version-2 file and return just the tickets list."""
        tickets = [
            {
                "id": "T001",
                "title": "V2 ticket",
                "category": "Software",
                "urgency": "medium",
                "affected_users": 5,
                "priority": "medium",
                "status": "open",
                "assigned_to": None,
            }
        ]
        events = [{"id": "E001", "ticket_id": "T001", "action": "create", "timestamp": "2026-10-14T10:00:00Z", "actor": "system", "details": {}}]
        save_data(tickets, events, self.data_path)

        extracted = load_tickets(self.data_path)
        self.assertEqual(extracted, tickets)

    def test_defensive_validation_rejects_missing_required_fields(self):
        """Missing mandatory ticket fields raise ValueError."""
        incomplete_ticket = {
            "id": "T001",
            "title": "Missing category and urgency",
        }
        with self.assertRaises(ValueError) as ctx:
            save_data([incomplete_ticket], [], self.data_path)
        self.assertIn("missing required field", str(ctx.exception))

    def test_defensive_validation_rejects_invalid_values(self):
        """Invalid categories, urgencies, or negative affected_users raise ValueError."""
        bad_category = {
            "id": "T001", "title": "Test", "category": "InvalidCat",
            "urgency": "high", "affected_users": 5, "priority": "high", "status": "open"
        }
        with self.assertRaises(ValueError) as ctx:
            save_data([bad_category], [], self.data_path)
        self.assertIn("invalid category", str(ctx.exception).lower())

        bad_users = {
            "id": "T001", "title": "Test", "category": "Network",
            "urgency": "high", "affected_users": 0, "priority": "high", "status": "open"
        }
        with self.assertRaises(ValueError) as ctx:
            save_data([bad_users], [], self.data_path)
        self.assertIn("affected_users must be a positive integer", str(ctx.exception))

    def test_defensive_validation_rejects_corrupted_timestamps(self):
        """Corrupted or naive timestamps in ticket records raise ValueError."""
        naive_ts_ticket = {
            "id": "T001", "title": "Test", "category": "Network",
            "urgency": "high", "affected_users": 5, "priority": "high", "status": "open",
            "created_at": "2026-10-14 12:00:00"  # Missing timezone offset
        }
        with self.assertRaises(ValueError) as ctx:
            save_data([naive_ts_ticket], [], self.data_path)
        self.assertIn("invalid utc timestamp", str(ctx.exception).lower())

    def test_defensive_validation_rejects_duplicate_ticket_ids(self):
        """Duplicate ticket IDs in collection raise ValueError."""
        duplicate_tickets = [
            {"id": "T001", "title": "First", "category": "Network", "urgency": "high", "affected_users": 5, "priority": "high", "status": "open"},
            {"id": "T001", "title": "Duplicate", "category": "Hardware", "urgency": "low", "affected_users": 2, "priority": "low", "status": "open"},
        ]
        with self.assertRaises(ValueError) as ctx:
            save_data(duplicate_tickets, [], self.data_path)
        self.assertIn("duplicate ticket id 't001'", str(ctx.exception).lower())

    def test_defensive_validation_rejects_duplicate_event_ids(self):
        """Duplicate event IDs in collection raise ValueError."""
        tickets = [{"id": "T001", "title": "First", "category": "Network", "urgency": "high", "affected_users": 5, "priority": "high", "status": "open"}]
        duplicate_events = [
            {"id": "E001", "ticket_id": "T001", "action": "create", "timestamp": "2026-10-14T10:00:00Z", "actor": "system", "details": {}},
            {"id": "E001", "ticket_id": "T001", "action": "escalate", "timestamp": "2026-10-14T11:00:00Z", "actor": "system", "details": {}},
        ]
        with self.assertRaises(ValueError) as ctx:
            save_data(tickets, duplicate_events, self.data_path)
        self.assertIn("duplicate event id 'e001'", str(ctx.exception).lower())

    def test_ticket_and_event_id_continuity_after_loading(self):
        """Sequential IDs for both tickets and events increment properly after reload."""
        tickets = [
            {"id": "T001", "title": "Ticket 1", "category": "Network", "urgency": "high", "affected_users": 5, "priority": "high", "status": "open"},
            {"id": "T008", "title": "Ticket 8", "category": "Network", "urgency": "high", "affected_users": 5, "priority": "high", "status": "open"},
        ]
        events = [
            {"id": "E001", "ticket_id": "T001", "action": "create", "timestamp": "2026-10-14T10:00:00Z", "actor": "system", "details": {}},
            {"id": "E014", "ticket_id": "T008", "action": "escalate", "timestamp": "2026-10-14T11:00:00Z", "actor": "system", "details": {}},
        ]
        save_data(tickets, events, self.data_path)

        loaded_tickets, loaded_events = load_data(self.data_path)
        next_tid = generate_ticket_id(loaded_tickets)
        next_eid = generate_event_id(loaded_events)

        self.assertEqual(next_tid, "T009")
        self.assertEqual(next_eid, "E015")


if __name__ == "__main__":
    unittest.main()
