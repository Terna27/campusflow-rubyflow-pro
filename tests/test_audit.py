import unittest
from unittest.mock import patch
from io import StringIO

from main import handle_audit_history


class TestAuditHistory(unittest.TestCase):

    def setUp(self):
        self.events = [
            {
                "id": "E001",
                "ticket_id": "T001",
                "action": "create",
                "actor": "Ummul",
                "timestamp": "2026-10-15T10:00:00Z",
                "details": {
                    "before_status": None,
                    "after_status": "open"
                }
            },
            {
                "id": "E002",
                "ticket_id": "T002",
                "action": "assign",
                "actor": "John",
                "timestamp": "2026-10-15T11:00:00Z",
                "details": {
                    "before_status": "open",
                    "after_status": "open",
                    "assigned_to": "John"
                }
            }
        ]

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.input", return_value="")
    def test_view_all_events(self, mock_input, mock_stdout):
        handle_audit_history(self.events)

        output = mock_stdout.getvalue()

        self.assertIn("E001", output)
        self.assertIn("E002", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.input", return_value="T001")
    def test_filter_events_by_ticket_id(self, mock_input, mock_stdout):
        handle_audit_history(self.events)

        output = mock_stdout.getvalue()

        self.assertIn("E001", output)
        self.assertNotIn("E002", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.input", return_value="T999")
    def test_nonexistent_ticket_history(self, mock_input, mock_stdout):
        handle_audit_history(self.events)

        output = mock_stdout.getvalue()

        self.assertIn("No audit history found", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.input", return_value="")
    def test_empty_audit_history(self, mock_input, mock_stdout):
        handle_audit_history([])

        output = mock_stdout.getvalue()

        self.assertIn("No audit history found", output)