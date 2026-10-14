# CampusFlow: Architecture & Design Decisions

## 1. Overview and Engineering Roles

CampusFlow is a Python command-line helpdesk application built collaboratively by two engineers:
- **Engineer A (Theophilus Jacob / tjayokanmi)**: Ticket creation (`create_ticket`), input validation, priority calculation (`calculate_priority`), and corresponding unit tests.
- **Engineer B (Terna Peter / Tena-byte)**: Ticket assignment (`assign_ticket`), ticket workflow transitions (`update_status`), explicit ticket reopening (`reopen_ticket`), priority-ordered work queue (`get_work_queue`), ticket reporting (`generate_report`), and corresponding unit tests.
- **Shared Ownership**: JSON persistence (`campusflow/storage.py`), CLI menu integration (`main.py`), and documentation.

---

## 2. Shared Data Model

Tickets are represented as standard Python dictionaries contained within a list (`list[dict]`).
Each ticket contains the following canonical 8 fields:

```python
{
    "id": "T001",                   # String: sequential identifier, e.g. "T001", "T002"
    "title": "Campus Wi-Fi down",   # String: non-empty, trimmed title
    "category": "Network",          # String: "Network", "Hardware", "Software", "Other"
    "urgency": "high",              # String: "low", "medium", "high"
    "affected_users": 15,           # Integer: positive integer (>= 1)
    "priority": "critical",         # String: "critical", "high", "medium", "low"
    "status": "open",               # String: "open", "in_progress", "resolved"
    "assigned_to": None             # String or None: staff member name or None
}
```

Tickets are initially created with `status="open"` and `assigned_to=None`.

---

## 3. Function Contracts & Interfaces

### 3.1 Feature F3: Ticket Assignment (`campusflow.workflow`)
```python
def assign_ticket(tickets: list[dict], ticket_id: str, staff_name: str) -> dict:
```
- **Inputs**:
  - `tickets`: List of ticket dictionaries.
  - `ticket_id`: Target ticket ID (e.g., `"T001"`).
  - `staff_name`: Name of assigned staff member.
- **Preconditions / Validation**:
  - `ticket_id` must match an existing ticket in `tickets`. If not found, raises `ValueError("Ticket <id> not found")`.
  - `staff_name` must be a non-empty string when trimmed. If empty or whitespace-only, raises `ValueError("Staff name cannot be empty")`.
  - A ticket with status `"resolved"` cannot be assigned. If attempted, raises `ValueError("Cannot assign a resolved ticket; reopen the ticket first")`.
- **Side Effects & Return**:
  - Modifies the ticket's `"assigned_to"` field in-place with the trimmed staff name.
  - Returns the updated ticket dictionary.
  - Leaves the ticket unchanged if any validation check fails.

---

### 3.2 Feature F4: Ticket Workflow & Lifecycle (`campusflow.workflow`)
```python
def update_status(tickets: list[dict], ticket_id: str, new_status: str) -> dict:
def reopen_ticket(tickets: list[dict], ticket_id: str) -> dict:
```
- **Allowed Statuses**: `"open"`, `"in_progress"`, `"resolved"`.
- **Workflow State Rules**:
  - Normalized status inputs (whitespace-stripped and lowercased).
  - `ticket_id` must match an existing ticket; otherwise raises `ValueError`.
  - Unrecognized status strings raise `ValueError("Invalid status: <status>")`.
  - An `"open"` ticket can move to `"in_progress"` **only** if `assigned_to` is not `None` and not empty. If unassigned, raises `ValueError("Ticket must be assigned before moving to in_progress")`.
  - An `"in_progress"` ticket can move to `"resolved"`.
  - An `"open"` ticket **cannot** move directly to `"resolved"`. Raises `ValueError("Cannot resolve an open ticket directly; must be in_progress first")`.
  - A `"resolved"` ticket **cannot** be modified via `update_status`. Any transition attempt on a resolved ticket raises `ValueError("Resolved tickets cannot be modified; use reopen_ticket")`.
  - Same-status transitions raise `ValueError("Ticket is already in '<status>' status")`.
- **Explicit Reopening (`reopen_ticket`)**:
  - Finds ticket by `ticket_id`.
  - Can **only** be performed on tickets whose current status is `"resolved"`. If ticket is not resolved, raises `ValueError("Only resolved tickets can be reopened")`.
  - Sets `ticket["status"] = "open"`.
  - Preserves existing `assigned_to` information so assigned staff can resume work or be reassigned.
  - Returns the updated ticket dictionary.

---

### 3.3 Feature F5: Work Queue (`campusflow.workflow`)
```python
def get_work_queue(tickets: list[dict]) -> list[dict]:
```
- **Filtering**:
  - Includes **only** tickets with status `"open"` or `"in_progress"`.
  - Strictly excludes `"resolved"` tickets.
- **Ordering**:
  - Primary sort: Priority in exact order: `"critical"` (rank 0) > `"high"` (rank 1) > `"medium"` (rank 2) > `"low"` (rank 3).
  - Secondary tie-breaker: Ascending numeric ticket ID (e.g., `"T002"` precedes `"T010"` by parsing the numeric portion `int(ticket_id[1:])`).
- **Policy for Unexpected Priority Values**:
  - If a ticket has an unknown or missing priority value not in the 4 canonical levels, `get_work_queue` raises `ValueError(f"Unexpected priority '{priority}' in ticket '{ticket_id}'")` to avoid silently misordering or corrupting the queue.
- **Side Effects**:
  - Non-destructive: returns a new sorted list without modifying the original collection order.
  - Handles empty input gracefully by returning `[]`.

---

### 3.4 Feature F6: Reports (`campusflow.reports`)
```python
def generate_report(tickets: list[dict]) -> dict:
```
- **Return Structure**:
  ```python
  {
      "total": int,
      "by_status": {
          "open": int,
          "in_progress": int,
          "resolved": int
      },
      "by_priority": {
          "critical": int,
          "high": int,
          "medium": int,
          "low": int
      }
  }
  ```
- **Requirements**:
  - Always includes all allowed statuses and priorities with integer count `0`, even if no tickets match.
  - For empty list `[]`, returns `total: 0` and all subcounts as `0`.
  - Does not mutate input list.

---

### 3.5 Feature F7: Shared JSON Persistence (`campusflow.storage`)
```python
def load_tickets(filepath: str = "data/tickets.json") -> list[dict]:
def save_tickets(tickets: list[dict], filepath: str = "data/tickets.json") -> None:
```
- **Loading Behavior**:
  - If `filepath` does not exist: returns empty list `[]` (fresh start).
  - If `filepath` exists and contains valid JSON list: returns loaded list.
  - If `filepath` contains malformed JSON or non-list root structure: raises `ValueError("Corrupted data file...")`. It **never** silently replaces corrupt data with an empty list.
- **Saving Behavior**:
  - Ensures parent directory exists (`os.makedirs`).
  - Uses atomic replacement (writes to a temporary file in the same directory, then calls `os.replace`) to protect against partial writes on crash or power loss.
- **Sequential Ticket IDs**:
  - Uses Engineer A's `generate_ticket_id(records)` logic.
  - When loading existing tickets on application startup, the highest existing numeric ID is preserved, guaranteeing unique sequential IDs across sessions.

---

## 4. Engineer A Integration Inspection & Coordination Items

During repository inspection of Engineer A's code in `campusflow/tickets.py` and `tests/test_priority.py`:
1. **Import Path in `campusflow/tickets.py`**:
   - Current line 1: `from priority import calculate_priority`.
   - Issue: When running tests or CLI from project root, raises `ModuleNotFoundError: No module named 'priority'`.
   - Proposed safe solution: Change to `from campusflow.priority import calculate_priority`.
2. **Missing Return Statement in `create_ticket`**:
   - `create_ticket` constructs `my_ticket` dict but omits `return my_ticket`.
   - Proposed safe solution: Add `return my_ticket`.
3. **Hardcoded ID in `create_ticket`**:
   - `create_ticket` hardcodes `"id": "T001"`.
   - Proposed safe solution: Support `records` parameter or pass existing tickets: `create_ticket(title, category, urgency, affected_users, records=None)`.
4. **Top-Level Print & Global Records in `campusflow/tickets.py`**:
   - `print(generate_ticket_id(records))` runs on module import, printing `"T008"`.
   - Proposed safe solution: Guard under `if __name__ == "__main__":` or remove scratch execution.
5. **Bare Assertions in `tests/test_priority.py`**:
   - Top-level `assert` statements fail with `NameError` under `python -m unittest discover` because `calculate_priority` is not imported and assertions are not inside a `unittest.TestCase`.
   - Proposed safe solution: Wrap assertions in a standard `unittest.TestCase` class with `from campusflow.priority import calculate_priority`.

---

## 5. CampusFlow Pro Architecture: Developer A Specifications & Shared Contracts

### 5.1 Deterministic UTC Time Handling (`campusflow/time_utils.py`)

- **Field Schema Extensions on Ticket**:
  - `created_at`: Canonical ISO-8601 UTC string (e.g., `"2026-10-14T10:00:00Z"`).
  - `updated_at`: Canonical ISO-8601 UTC string.
  - `due_at`: Canonical ISO-8601 UTC string calculated from priority SLA duration.
  - `escalation_cycle`: Non-negative integer initialized to `0`.
- **Timezone Awareness & Naive Rejection**:
  - All internal calculations use timezone-aware `datetime` objects (`timezone.utc`).
  - Naive datetimes (where `tzinfo is None` or `tzinfo.utcoffset is None`) and naive ISO strings (e.g. `"2026-10-14T12:00:00"`) are strictly rejected with a descriptive `ValueError`.
  - Non-UTC timezone offsets (e.g. `+02:00`) are parsed and normalized into UTC.
- **Clock Injection**:
  - Every time-dependent operation accepts an optional injected `now` parameter (`datetime | str | None`).
  - When `now` is omitted, the UTC system clock is resolved exactly once per operation (`resolve_now(now)`).
  - Automated tests inject static timestamps, eliminating `time.sleep()` calls and ensuring determinism.
- **Bidirectional Equality (`UTCTimestamp`)**:
  - Inherits from `str` to serialize directly with `json.dump()`.
  - Implements `__eq__` so that comparisons against timezone-aware `datetime` objects evaluate to `True` when representing the same instant.

---

### 5.2 SLA Due Date Calculation & Overdue Detection (`campusflow/sla.py`)

- **SLA Durations by Priority**:
  - `critical`: 60 minutes (1 hour)
  - `high`: 240 minutes (4 hours)
  - `medium`: 1440 minutes (24 hours)
  - `low`: 2880 minutes (48 hours)
- **`calculate_due_at(priority, cycle_start)`**:
  - Computes: `cycle_start + SLA_DURATIONS_MINUTES[priority]`.
  - Accepts priority as string (`"critical"`, `"high"`, `"medium"`, `"low"`) or as a ticket dictionary (extracting `ticket["priority"]` and `ticket["created_at"]` / `ticket["updated_at"]`).
  - Returns `UTCTimestamp` formatted in ISO-8601 UTC ending with `Z`.
  - Rejects unknown priorities or naive timestamps with `ValueError`.
- **`is_overdue(ticket, now)`**:
  - Returns `False` if `ticket["status"] == "resolved"`.
  - Returns `False` if `due_at` is absent or `now <= due_at`.
  - Returns `True` if ticket is active (`open` or `in_progress`) and `now > due_at`.
- **`escalate_overdue(tickets, events, now, actor)`**:
  - Resolves UTC clock once for the batch operation.
  - Scans all tickets with `is_overdue(ticket, now)`.
  - Increments `escalation_cycle` by 1.
  - Updates `updated_at` to `now`.
  - Recalculates `due_at` from `now` based on ticket priority SLA.
  - Appends an audit event to `events` with action `"escalate"`.
  - Returns list of escalated tickets.

---

### 5.3 Version-2 JSON Persistence Architecture (`campusflow/storage.py`)

- **Version-2 Container Format**:
  ```json
  {
    "version": 2,
    "tickets": [ ... ],
    "events": [ ... ]
  }
  ```
- **Defensive Validation Rules (`validate_ticket_record`, `validate_event`)**:
  - Root container must be a dictionary specifying `"version": 2` with `"tickets"` and `"events"` lists (or a list for v1 backward compatibility).
  - Validates ticket required fields (`id`, `title`, `category`, `urgency`, `affected_users`, `priority`, `status`).
  - Strictly enforces positive integer `affected_users` (`>= 1`, not `bool`, not negative/zero).
  - Validates explicit ISO-8601 UTC timestamps on `created_at`, `updated_at`, `due_at`.
  - Enforces global ticket ID uniqueness and event ID uniqueness across collections.
  - Missing file allows clean startup returning `([], [])`.
  - Corrupt or malformed JSON raises `ValueError` immediately without silent data erasure.
- **Atomic File Replacement**:
  - Writes to a temporary file in the target directory using `tempfile.NamedTemporaryFile`.
  - Flushes and syncs file descriptor (`os.fsync`) to physical disk.
  - Atomically replaces target via `os.replace`.
- **Backward Compatibility**:
  - `load_data`: Supports loading legacy Version-1 files (returns `(tickets, [])`) and Version-2 files (returns `(tickets, events)`).
  - `load_tickets`: Seamlessly reads legacy v1 lists and extracts `tickets` from v2 container.
  - `save_data`: Atomically saves Version-2 payload with defensive validation.
  - `save_tickets`: Preserved for legacy Version-1 list-only callers.

---

### 5.4 Ticket & Event ID Continuity (`campusflow/tickets.py`, `campusflow/events.py`)

- **Ticket IDs**: `generate_ticket_id(records)` parses numeric suffixes across existing tickets and returns `f"T{max_id + 1:03d}"` (defaults to `"T001"` if empty).
- **Event IDs**: `generate_event_id(events)` parses numeric suffixes across existing events and returns `f"E{max_id + 1:03d}"` (defaults to `"E001"` if empty).
- **Session Continuity**: Both generators preserve the highest sequential identifier after loading from disk, preventing ID collision or duplication across restarts.

---

### 5.5 Developer B Integration Contract & Reopening Hooks

To coordinate between Developer A (Core/SLA/Persistence) and Developer B (Workflow/History/CLI), the following shared integration contracts are established:

1. **Shared Event Schema**:
   ```python
   {
       "id": "E001",                   # String: sequential identifier via generate_event_id
       "ticket_id": "T001",            # String: associated ticket ID
       "action": "create",             # String: operation name ('create', 'assign', 'status_change', 'reopen', 'escalate')
       "timestamp": "2026-10-14T10:00:00Z", # String: ISO-8601 UTC timestamp
       "actor": "admin",               # String: user or system actor
       "details": {}                   # Dict: operation metadata
   }
   ```
2. **Event Helper Contract (`campusflow.events.record_event`)**:
   - Developer B can record any operational history by invoking:
     ```python
     record_event(events, ticket_id=ticket["id"], action=action, actor=actor, timestamp=now, details={...})
     ```
3. **Creation Hook for Developer B**:
   - When Developer B processes ticket creation, call `create_ticket(..., now=now)`.
   - `create_ticket` automatically initializes `created_at`, `updated_at`, `due_at`, and `escalation_cycle = 0`.
   - Developer B then records the creation event:
     ```python
     record_event(events, ticket_id=ticket["id"], action="create", actor=actor, timestamp=ticket["created_at"], details={"priority": ticket["priority"]})
     ```
4. **Reopening Hook for Developer B**:
   - When a resolved ticket is reopened via `reopen_ticket`:
     - Ticket status transitions back to `"open"`.
     - SLA window restarts: Developer B computes new deadline:
       `ticket["due_at"] = calculate_due_at(ticket["priority"], cycle_start=now)`
     - Ticket timestamp is updated:
       `ticket["updated_at"] = format_utc_iso(now)`
     - Reopening event is recorded:
       ```python
       record_event(events, ticket_id=ticket["id"], action="reopen", actor=actor, timestamp=format_utc_iso(now), details={"due_at": ticket["due_at"]})
       ```

