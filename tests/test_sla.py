"""Unit tests for deterministic UTC time handling, SLA deadlines, overdue detection, and escalation."""

import unittest
from datetime import datetime, timezone, timedelta

from campusflow.time_utils import (
    parse_utc_iso,
    format_utc_iso,
    resolve_now,
    UTCTimestamp,
)
from campusflow.sla import (
    calculate_due_at,
    is_overdue,
    escalate_overdue,
    SLA_DURATIONS_MINUTES,
)
from campusflow.events import generate_event_id, record_event, validate_event
from campusflow.tickets import create_ticket


class TestUTCTimeHandling(unittest.TestCase):
    """Test deterministic UTC time handling and naive timestamp rejection."""

    def test_parse_valid_utc_iso_string_with_z(self):
        """Timestamp ending with 'Z' is parsed to UTC timezone-aware datetime."""
        ts_str = "2026-10-14T12:00:00Z"
        dt = parse_utc_iso(ts_str)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 12)

    def test_parse_valid_utc_iso_string_with_numeric_offset(self):
        """Timestamp with explicit non-zero offset is normalized to UTC."""
        ts_str = "2026-10-14T14:00:00+02:00"
        dt = parse_utc_iso(ts_str)
        self.assertEqual(dt.tzinfo, timezone.utc)
        # 14:00 +02:00 is 12:00 UTC
        self.assertEqual(dt.hour, 12)

    def test_reject_naive_timestamp_string(self):
        """Timestamp string without explicit timezone raises ValueError."""
        naive_str = "2026-10-14T12:00:00"
        with self.assertRaises(ValueError) as ctx:
            parse_utc_iso(naive_str)
        self.assertIn("naive", str(ctx.exception).lower())

    def test_reject_naive_datetime_object(self):
        """Naive datetime object without tzinfo raises ValueError."""
        naive_dt = datetime(2026, 10, 14, 12, 0, 0)
        with self.assertRaises(ValueError) as ctx:
            parse_utc_iso(naive_dt)
        self.assertIn("naive", str(ctx.exception).lower())

    def test_reject_invalid_timestamp_formats(self):
        """Malformed date strings raise ValueError."""
        for invalid in ["not-a-date", "", "   ", "2026-13-45T99:99:99Z"]:
            with self.assertRaises(ValueError):
                parse_utc_iso(invalid)

    def test_format_utc_iso_produces_canonical_z_string(self):
        """format_utc_iso produces clean ISO-8601 string ending with Z."""
        dt = datetime(2026, 10, 14, 15, 30, 0, tzinfo=timezone.utc)
        iso = format_utc_iso(dt)
        self.assertEqual(iso, "2026-10-14T15:30:00Z")

    def test_utc_timestamp_class_equality(self):
        """UTCTimestamp compares equal to both string and timezone-aware datetime."""
        dt = datetime(2026, 10, 14, 15, 30, 0, tzinfo=timezone.utc)
        ts = UTCTimestamp("2026-10-14T15:30:00Z")
        self.assertEqual(ts, dt)
        self.assertEqual(dt, ts)
        self.assertEqual(ts, "2026-10-14T15:30:00Z")
        self.assertEqual(ts.as_datetime, dt)


class TestCalculateDueAt(unittest.TestCase):
    """Test calculate_due_at with all SLA priorities and boundaries."""

    def setUp(self):
        self.cycle_start = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)

    def test_sla_duration_constants(self):
        """SLA durations match exact requirements."""
        self.assertEqual(SLA_DURATIONS_MINUTES["critical"], 60)
        self.assertEqual(SLA_DURATIONS_MINUTES["high"], 240)
        self.assertEqual(SLA_DURATIONS_MINUTES["medium"], 1440)
        self.assertEqual(SLA_DURATIONS_MINUTES["low"], 2880)

    def test_calculate_due_at_critical(self):
        """Critical priority has 60 minutes SLA."""
        due = calculate_due_at("critical", self.cycle_start)
        expected = self.cycle_start + timedelta(minutes=60)
        self.assertEqual(due, expected)
        self.assertEqual(due, "2026-10-14T11:00:00Z")

    def test_calculate_due_at_high(self):
        """High priority has 240 minutes (4 hours) SLA."""
        due = calculate_due_at("high", self.cycle_start)
        expected = self.cycle_start + timedelta(minutes=240)
        self.assertEqual(due, expected)
        self.assertEqual(due, "2026-10-14T14:00:00Z")

    def test_calculate_due_at_medium(self):
        """Medium priority has 1440 minutes (24 hours) SLA."""
        due = calculate_due_at("medium", self.cycle_start)
        expected = self.cycle_start + timedelta(minutes=1440)
        self.assertEqual(due, expected)
        self.assertEqual(due, "2026-10-15T10:00:00Z")

    def test_calculate_due_at_low(self):
        """Low priority has 2880 minutes (48 hours) SLA."""
        due = calculate_due_at("low", self.cycle_start)
        expected = self.cycle_start + timedelta(minutes=2880)
        self.assertEqual(due, expected)
        self.assertEqual(due, "2026-10-16T10:00:00Z")

    def test_calculate_due_at_with_iso_string_input(self):
        """calculate_due_at accepts ISO-8601 string as cycle_start."""
        due = calculate_due_at("critical", "2026-10-14T10:00:00Z")
        self.assertEqual(due, "2026-10-14T11:00:00Z")

    def test_calculate_due_at_with_ticket_dict(self):
        """calculate_due_at accepts ticket dictionary as first argument."""
        ticket = {
            "id": "T001",
            "priority": "high",
            "created_at": "2026-10-14T10:00:00Z",
        }
        due = calculate_due_at(ticket)
        self.assertEqual(due, "2026-10-14T14:00:00Z")

    def test_calculate_due_at_rejects_invalid_priority(self):
        """Invalid priority raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calculate_due_at("urgent", self.cycle_start)
        self.assertIn("invalid priority", str(ctx.exception).lower())

    def test_calculate_due_at_rejects_naive_cycle_start(self):
        """Naive datetime raises ValueError."""
        naive_dt = datetime(2026, 10, 14, 10, 0, 0)
        with self.assertRaises(ValueError):
            calculate_due_at("high", naive_dt)


class TestIsOverdue(unittest.TestCase):
    """Test overdue ticket detection with fixed clocks."""

    def setUp(self):
        self.start = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)
        self.ticket = {
            "id": "T001",
            "status": "open",
            "priority": "critical",
            "due_at": "2026-10-14T11:00:00Z",
        }

    def test_ticket_not_overdue_before_deadline(self):
        """Ticket is not overdue before deadline."""
        now = datetime(2026, 10, 14, 10, 59, 0, tzinfo=timezone.utc)
        self.assertFalse(is_overdue(self.ticket, now=now))

    def test_ticket_not_overdue_at_exact_deadline(self):
        """Ticket is not overdue at the exact deadline boundary."""
        now = datetime(2026, 10, 14, 11, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(is_overdue(self.ticket, now=now))

    def test_ticket_overdue_after_deadline(self):
        """Ticket is overdue 1 second after deadline."""
        now = datetime(2026, 10, 14, 11, 0, 1, tzinfo=timezone.utc)
        self.assertTrue(is_overdue(self.ticket, now=now))

    def test_in_progress_ticket_can_be_overdue(self):
        """In-progress tickets can also be overdue."""
        self.ticket["status"] = "in_progress"
        now = datetime(2026, 10, 14, 11, 30, 0, tzinfo=timezone.utc)
        self.assertTrue(is_overdue(self.ticket, now=now))

    def test_resolved_ticket_is_never_overdue(self):
        """Resolved tickets are never overdue regardless of time."""
        self.ticket["status"] = "resolved"
        now = datetime(2026, 10, 14, 15, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(is_overdue(self.ticket, now=now))

    def test_reject_naive_clock_injection(self):
        """Naive clock injected into is_overdue raises ValueError."""
        naive_now = datetime(2026, 10, 14, 12, 0, 0)
        with self.assertRaises(ValueError):
            is_overdue(self.ticket, now=naive_now)


class TestEscalateOverdue(unittest.TestCase):
    """Test overdue ticket escalation, SLA cycle increment, and audit events."""

    def setUp(self):
        self.fixed_now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
        self.tickets = [
            {
                "id": "T001",
                "title": "Wi-Fi down",
                "priority": "critical",
                "status": "open",
                "created_at": "2026-10-14T10:00:00Z",
                "updated_at": "2026-10-14T10:00:00Z",
                "due_at": "2026-10-14T11:00:00Z",  # Overdue (11:00 < 12:00)
                "escalation_cycle": 0,
            },
            {
                "id": "T002",
                "title": "Broken mouse",
                "priority": "low",
                "status": "open",
                "created_at": "2026-10-14T10:00:00Z",
                "updated_at": "2026-10-14T10:00:00Z",
                "due_at": "2026-10-16T10:00:00Z",  # Not overdue
                "escalation_cycle": 0,
            },
            {
                "id": "T003",
                "title": "Old resolved ticket",
                "priority": "critical",
                "status": "resolved",
                "created_at": "2026-10-14T08:00:00Z",
                "updated_at": "2026-10-14T09:00:00Z",
                "due_at": "2026-10-14T09:00:00Z",  # Passed deadline, but resolved
                "escalation_cycle": 0,
            },
        ]
        self.events = []

    def test_escalate_overdue_updates_ticket_and_appends_event(self):
        """Overdue active ticket is escalated and an event is appended."""
        escalated = escalate_overdue(
            self.tickets,
            self.events,
            now=self.fixed_now,
            actor="supervisor_bot",
        )

        self.assertEqual(len(escalated), 1)
        self.assertEqual(escalated[0]["id"], "T001")

        # Ticket T001 state changes
        t1 = self.tickets[0]
        self.assertEqual(t1["escalation_cycle"], 1)
        self.assertEqual(t1["updated_at"], "2026-10-14T12:00:00Z")
        # Critical SLA is 60m: 12:00 + 60m = 13:00
        self.assertEqual(t1["due_at"], "2026-10-14T13:00:00Z")

        # Non-overdue and resolved tickets remain unchanged
        self.assertEqual(self.tickets[1]["escalation_cycle"], 0)
        self.assertEqual(self.tickets[2]["escalation_cycle"], 0)

        # Audit event verification
        self.assertEqual(len(self.events), 1)
        event = self.events[0]
        self.assertEqual(event["id"], "E001")
        self.assertEqual(event["ticket_id"], "T001")
        self.assertEqual(event["action"], "escalate")
        self.assertEqual(event["actor"], "supervisor_bot")
        self.assertEqual(event["timestamp"], "2026-10-14T12:00:00Z")
        self.assertEqual(event["details"]["escalation_cycle"], 1)
        self.assertEqual(event["details"]["new_due_at"], "2026-10-14T13:00:00Z")

    def test_escalate_overdue_repeated_cycles(self):
        """Subsequent overdue check advances to cycle 2."""
        escalate_overdue(self.tickets, self.events, now=self.fixed_now)
        self.assertEqual(self.tickets[0]["escalation_cycle"], 1)

        # Move clock past the new deadline (13:00) to 14:00
        cycle_2_now = datetime(2026, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
        escalate_overdue(self.tickets, self.events, now=cycle_2_now)

        self.assertEqual(self.tickets[0]["escalation_cycle"], 2)
        self.assertEqual(self.tickets[0]["due_at"], "2026-10-14T15:00:00Z")
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[1]["id"], "E002")


class TestEventHelpers(unittest.TestCase):
    """Test event ID generation and recording."""

    def test_generate_event_id_empty(self):
        """Empty events list starts with E001."""
        self.assertEqual(generate_event_id([]), "E001")

    def test_generate_event_id_sequential(self):
        """Sequential IDs increment from max existing ID."""
        events = [{"id": "E001"}, {"id": "E004"}]
        self.assertEqual(generate_event_id(events), "E005")

    def test_record_event_appends_and_returns(self):
        """record_event adds valid event to collection."""
        events = []
        ev = record_event(
            events,
            ticket_id="T001",
            action="create",
            actor="admin",
            timestamp="2026-10-14T10:00:00Z",
            details={"priority": "critical"},
        )
        self.assertEqual(ev["id"], "E001")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["ticket_id"], "T001")


class TestTicketCreationWithTime(unittest.TestCase):
    """Test ticket creation initializes SLA timestamps and escalation cycle."""

    def test_create_ticket_includes_utc_timestamps_and_due_at(self):
        """create_ticket adds created_at, updated_at, due_at, and escalation_cycle."""
        fixed_now = datetime(2026, 10, 14, 9, 0, 0, tzinfo=timezone.utc)
        ticket = create_ticket(
            title="Database server unresponsive",
            category="Software",
            urgency="high",
            affected_users=15,
            now=fixed_now,
        )

        self.assertEqual(ticket["priority"], "critical")
        self.assertEqual(ticket["created_at"], "2026-10-14T09:00:00Z")
        self.assertEqual(ticket["updated_at"], "2026-10-14T09:00:00Z")
        # Critical SLA is 60m: 9:00 + 60m = 10:00
        self.assertEqual(ticket["due_at"], "2026-10-14T10:00:00Z")
        self.assertEqual(ticket["escalation_cycle"], 0)


if __name__ == "__main__":
    unittest.main()
