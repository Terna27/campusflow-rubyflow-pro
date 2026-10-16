# CampusFlow

CampusFlow is a robust command-line helpdesk ticket management system built with Python's standard library. It enables campus technical support staff to record, prioritize, assign, track, queue, and report on technical support incidents.

This repository features the **CampusFlow Pro** upgrades, including deterministic UTC time handling, priority-based SLA due date calculation, overdue incident escalation cycles, event audit trails, and Version-2 JSON persistence with defensive schema validation.

---

## Team Roles & Ownership

The application is co-developed by a two-engineer team:

- **Engineer A (Theophilus Jacob / @tjayokanmi)**:
  - Ticket creation (`create_ticket`) and unique sequential ID generation (`generate_ticket_id`).
  - Input validation (non-empty titles, valid categories, positive integer user counts).
  - Priority calculation engine (`calculate_priority`).
  - **CampusFlow Pro**: Deterministic UTC time handling (`campusflow/time_utils.py`).
  - **CampusFlow Pro**: SLA due date calculation (`calculate_due_at`), overdue detection (`is_overdue`), and escalation (`escalate_overdue`) (`campusflow/sla.py`).
  - **CampusFlow Pro**: Version-2 JSON persistence with defensive schema validation and atomic file replacement (`campusflow/storage.py`).
  - **CampusFlow Pro**: Event model, sequential event ID generation (`generate_event_id`), and Developer B history recording contract (`campusflow/events.py`).
  - Ticket creation, priority, SLA, and persistence test suites (`test_priority.py`, `test_tickets.py`, `test_sla.py`, `test_storage_v2.py`).

- **Engineer B (Terna Peter / @Tena-byte)**:
  - Ticket assignment (`assign_ticket`).
  - Ticket lifecycle workflow state machine (`update_status`) and explicit reopening (`reopen_ticket`).
  - Prioritized work queue with numeric ID tie-breaking (`get_work_queue`).
  - System reporting and aggregate metrics (`generate_report`).
  - Workflow, queue, and reporting test suites (`test_workflow.py`, `test_reports.py`).

- **Shared Responsibilities**:
  - Safe JSON persistence with atomic replacement (`campusflow/storage.py`, `test_storage.py`).
  - Interactive CLI integration (`main.py`).
  - System architecture documentation (`docs/design-decisions.md`) and AI learning logs (`docs/ai-learning-log.md`).

---

## Features (F1–F7 + Pro)

- **F1 — Ticket Creation**: Create support requests with title, category, urgency, and affected users. Automatically computes priority using rule hierarchy and assigns sequential IDs (`T001`, `T002`, ...). Automatically timestamps in UTC and computes initial SLA due date.
- **F2 — List & View Details**: Browse all active and resolved tickets, or inspect individual ticket details including SLA deadlines and escalation cycle numbers.
- **F3 — Assignment**: Assign tickets to staff members; prevents whitespace-only names and rejects assigning resolved tickets without reopening.
- **F4 — Workflow Lifecycle**: Enforces state machine (`open` -> `in_progress` -> `resolved`). Disallows moving to `in_progress` without assignment, forbids direct resolution from `open`, and requires explicit reopening for `resolved` tickets.
- **F5 — Work Queue**: Displays active, unresolved tickets sorted by priority (`critical` > `high` > `medium` > `low`) with deterministic tie-breaking based on numeric ticket IDs (`T002` before `T010`).
- **F6 — Reports**: Generates summary statistics including total ticket count and complete breakdowns across all valid statuses and priorities (preserving zero-count entries).
- **F7 — JSON Persistence (Version 2)**: Persists tickets and audit events across sessions using atomic file replacement (`tempfile` + `os.replace`). Supports Version-2 container schema (`{"version": 2, "tickets": [...], "events": [...]}`) with defensive schema validation while maintaining backward compatibility with Version-1 lists.
- **Pro — Deterministic UTC Time Handling**: Strict timezone-aware datetimes internally; ISO-8601 UTC strings with explicit timezone offsets on storage. Rejects naive timestamps with clear errors. Supports clock injection for reproducible, non-sleeping unit tests.
- **Pro — Priority SLA Engine**:
  - `critical`: 60 minutes
  - `high`: 240 minutes
  - `medium`: 1440 minutes
  - `low`: 2880 minutes
- **Pro — Overdue Escalation**: Identifies overdue active tickets, advances `escalation_cycle` counter, updates `updated_at`, recalculates `due_at` from the escalation instant, and writes an audit event to `events`.
- **Pro — ID Continuity**: Guarantees uninterrupted sequential ID generation for both tickets (`T...`) and events (`E...`) across process restarts.

---

## Architecture & Project Structure

```text
campusflow-rubyflow-pro/
├── campusflow/
│   ├── __init__.py
│   ├── priority.py         # Priority calculation engine (Engineer A)
│   ├── tickets.py          # Ticket creation, SLA timestamps & ID generation (Engineer A)
│   ├── time_utils.py       # Deterministic UTC time handling & naive rejection (Engineer A)
│   ├── sla.py              # SLA calculation, overdue detection & escalation (Engineer A)
│   ├── events.py           # Event model, ID generator & Developer B contract (Engineer A)
│   ├── storage.py          # Version-2 JSON persistence & defensive validation (Engineer A / Shared)
│   ├── workflow.py         # Assignment, lifecycle state machine, work queue (Engineer B)
│   └── reports.py          # Reporting metrics (Engineer B)
├── tests/
│   ├── __init__.py
│   ├── test_priority.py    # Priority engine tests
│   ├── test_tickets.py     # Ticket creation & validation tests
│   ├── test_sla.py         # UTC time handling, SLA deadlines & escalation tests (Engineer A)
│   ├── test_storage.py     # Legacy JSON persistence tests
│   ├── test_storage_v2.py  # Version-2 persistence, defensive validation & ID continuity tests (Engineer A)
│   ├── test_workflow.py    # Assignment, workflow, and queue tests
│   └── test_reports.py     # Reporting tests
├── docs/
│   ├── design-decisions.md # Architectural agreements, contracts & Pro specifications
│   └── ai-learning-log.md  # Deliberate AI learning records & reflection prompts
├── data/                   # Local application runtime data (git-ignored)
│   └── tickets.json
├── main.py                 # Interactive CLI entry point
├── README.md
└── .gitignore
```

---

## Getting Started

### Prerequisites
- Python 3.10+ (Standard library only; no external dependencies required)

### Running the Application

Run the interactive CLI:

```bash
python3 main.py
```

### Running Automated Tests

Run the complete automated test suite using `unittest`:

```bash
python3 -m unittest discover -s tests -v
```

All 80 automated tests pass without warning or failure:
- `test_priority.py`: 1 test (priority calculation boundaries)
- `test_tickets.py`: 7 tests (creation validation, boundary checks, ID generation)
- `test_workflow.py`: 22 tests (assignment, transition matrix, unassigned guards, reopening, queue sorting, tie-breaking)
- `test_reports.py`: 5 tests (empty lists, mixed counts, zero-count preservation, mutation checks)
- `test_storage.py`: 7 tests (round-trip persistence, atomic replacement, corruption handling, sequential ID reload)
- `test_sla.py`: 28 tests (UTC parsing, naive rejection, SLA durations, overdue detection, escalation cycles, event logging)
- `test_storage_v2.py`: 10 tests (Version-2 schema round-trip, defensive validation, v1 compatibility, ID continuity across reload)

---

## Known Limitations & Considerations

1. **Terminal-Only Interface**: CampusFlow is designed as a focused command-line tool using standard terminal input.
2. **Local Single-File Storage**: Persistence uses a local JSON file (`data/tickets.json`). For multi-user concurrent production setups, a database backend with transaction locking would be recommended.
3. **Staff Directory**: Staff names are currently validated as non-empty strings. A dedicated staff directory entity could be introduced in a future sprint.
