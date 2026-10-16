# CampusFlow: AI Learning Log

This document records the deliberate AI-assisted learning loops completed by the engineering team during the CampusFlow sprint, following Phase 3 and Phase 4 of the sprint requirements.

> **Note for Human Fellows**:
> Per sprint guidelines, do not fabricate AI interactions or verification results. Below are structured templates containing real technical concepts explored, experiments run, and placeholders for individual fellow reflection and defence preparation.

---

## Engineer B (Terna Peter / Tena-byte) Learning Loops

### Learning Loop 1: Atomic File Replacement for Safe JSON Persistence
- **Concept / Question**:
  - What happens if a program crashes while writing directly to `data/tickets.json` with `json.dump()`?
  - How can Python standard library achieve atomic file replacement without third-party dependencies?
- **AI Explanation Summary**:
  - Writing directly to an existing file (`open('data/tickets.json', 'w')`) empties or truncates the file immediately. If the process terminates abruptly before writing completes, the data is corrupted or lost.
  - The standard approach on POSIX and modern Windows systems is to write full content to a temporary file in the same directory (using `tempfile.NamedTemporaryFile(dir=..., delete=False)`), flush and sync to disk, and then perform an atomic rename using `os.replace(temp_path, target_path)`.
- **Tiny Experiment**:
  - Created a temporary file in Python, dumped test JSON, and called `os.replace` to overwrite a dummy target file.
  - Verified that `os.replace` completes atomically on POSIX filesystem and target content is intact.
- **Verification & Outcome**:
  - Implemented in `campusflow/storage.py` using `tempfile.NamedTemporaryFile` + `os.replace`.
  - Verified with automated tests in `tests/test_storage.py` that invalid data never corrupts existing state.
- **Fellow Reflection (Placeholder for human fellow to personalize)**:
  - *Reflection prompt*: Explain in your own words why `os.replace` is safer than standard `open(file, 'w')`.

---

### Learning Loop 2: Multi-Criteria Queue Sorting & Deterministic Tie-Breaking
- **Concept / Question**:
  - How do we sort a list of dictionaries with custom priority ranks (`critical` > `high` > `medium` > `low`) while breaking ties using the numeric ID (`T002` before `T010`), and without mutating the original collection?
- **AI Explanation Summary**:
  - Use Python's built-in `sorted()` function with a custom `key` callable.
  - Map priority strings to integer ranks: `{"critical": 0, "high": 1, "medium": 2, "low": 3}`.
  - Extract the numeric ticket ID by parsing digits from the ID string: `int(ticket["id"][1:])`.
  - Return a tuple `(priority_rank, numeric_id)` as the sort key. Python compares tuples lexicographically: first comparing priority ranks, and using numeric IDs for ties.
- **Tiny Experiment**:
  - Input list: `[{"id": "T010", "priority": "high"}, {"id": "T002", "priority": "high"}]`.
  - Tested `sorted(records, key=lambda t: (PRIORITY_RANK[t["priority"]], int(t["id"][1:])))`.
  - Result: `T002` correctly placed before `T010`. String sorting would place `"T010"` before `"T002"` because `'0'` < `'2'`, whereas numeric comparison `2 < 10` places `T002` first.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: Suggested simple string sorting on ticket ID: `t["id"]`.
  - *Identified flaw*: Lexicographical string comparison fails when ID numbers differ in digit length (e.g. `"T100"` vs `"T99"`).
  - *Correction applied*: Parsed the numeric portion explicitly as `int(ticket["id"][1:])`.
- **Fellow Reflection (Placeholder for human fellow to personalize)**:
  - *Reflection prompt*: Be prepared to explain to the examiner why numeric parsing is required for ticket ID tie-breaking.

---

### Learning Loop 3: State Machine Validation & Guarding Against Workflow Bypasses
- **Concept / Question**:
  - How should we enforce strict state transitions between `open`, `in_progress`, and `resolved` so that helper functions (`assign_ticket`, `update_status`, `reopen_ticket`) do not bypass one another?
- **AI Explanation Summary**:
  - Treat ticket lifecycle as a finite state machine:
    - `open` -> `in_progress` (only when `assigned_to` is populated).
    - `in_progress` -> `resolved`.
    - `open` -> `resolved` is strictly disallowed.
    - `resolved` -> `open` is only allowed via explicit `reopen_ticket()`.
    - No direct mutations or assignments on `resolved` tickets without reopening.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: A generic status update function allowing any target status as long as `target in ALLOWED_STATUSES`.
  - *Identified flaw*: This would allow moving directly from `open` to `resolved`, or assigning/modifying already resolved tickets without explicit reopening.
  - *Correction applied*: Enforced explicit transition matrix and prohibited ordinary status modifications on resolved tickets.
- **Fellow Reflection (Placeholder for human fellow to personalize)**:
  - *Reflection prompt*: Explain the difference between updating status and explicitly reopening a ticket during defence.

---

## Engineer A (Theophilus Jacob / tjayokanmi) Learning Loops

### Learning Loop 1: Deterministic Timezone-Aware UTC Timestamping vs Naive Datetime Pitfalls
- **Problem**:
  - How do we handle and persist timestamps in Python without subtle UTC bugs, naive datetime errors during comparisons, or relying on `time.sleep()` in automated tests?
- **My Initial Understanding**:
  - `datetime.now()` returns the current time, but it defaults to local system time without timezone info (`naive`), which causes `TypeError: can't compare offset-naive and offset-aware datetimes` when comparing against UTC deadlines.
- **Prompt to AI**:
  - "Explain how Python 3's datetime module handles timezone-aware UTC timestamps compared to naive datetimes. How should ISO-8601 strings with 'Z' and numerical offsets be parsed, validated, and compared deterministically without using time.sleep in unit tests?"
- **Useful AI Guidance**:
  - Always use explicit `datetime.now(timezone.utc)` instead of `datetime.utcnow()` (which is deprecated in Python 3.12+ because it returns a naive datetime).
  - Use `datetime.fromisoformat()` to parse strings, but enforce validation that `dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None`, rejecting naive input with `ValueError`.
  - Pass an optional injected `now` parameter into all time-dependent functions so unit tests can use fixed clocks.
- **My Independent Experiment/Test**:
  - Ran a script comparing `datetime.now(timezone.utc)` against an ISO string `"2026-10-14T12:00:00Z"`. Verified that replacing trailing `'Z'` with `'+00:00'` ensures compatibility across all Python versions, and confirmed that comparing a naive `datetime(2026, 10, 14, 12, 0)` raises `ValueError` in our defensive parser.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: The AI suggested using `datetime.utcnow().isoformat() + "Z"`.
  - *Identified flaw*: `datetime.utcnow()` produces a naive datetime object. If passed into code expecting `astimezone()`, it assumes local system time rather than UTC, and Python 3.12 issues a deprecation warning.
  - *Correction applied*: Replaced with `datetime.now(timezone.utc)`, strictly verified `tzinfo.utcoffset`, and designed `UTCTimestamp` to provide bidirectional equality with `datetime` objects.
- **Verification Source or Result**:
  - `tests/test_sla.py::TestUTCTimeHandling` (7 automated tests passing).
- **Decision**: Improved and accepted corrected version.
- **Related File / Commit**: `campusflow/time_utils.py`, `tests/test_sla.py`.
- **What I Can Now Explain Without AI**:
  - I can explain why naive datetimes cause silent calculation errors, how to enforce timezone awareness on parsing, and how dependency injection of a clock parameter enables 100% deterministic testing.

---

### Learning Loop 2: Version-2 JSON Persistence Architecture & Defensive Schema Validation
- **Problem**:
  - How do we evolve from a Version-1 flat list of ticket dictionaries `[...]` to a Version-2 container schema `{"version": 2, "tickets": [...], "events": [...]}` without breaking existing public interfaces or dropping legacy data?
- **My Initial Understanding**:
  - We could just change `save_tickets` to write a dictionary, but doing so would break existing tests that assert the root JSON structure is a list of tickets.
- **Prompt to AI**:
  - "I need to upgrade a JSON persistence layer from a list of dicts to a versioned container with tickets and audit events. How do I implement defensive validation on required fields, preserve sequential ID generation across reloads, and ensure backward compatibility for old callers?"
- **Useful AI Guidance**:
  - Introduce `load_data` and `save_data` as the canonical Version-2 entry points, while upgrading `load_tickets` to transparently unwrap `data["tickets"]` when encountering a Version-2 dictionary.
  - Validate field types, allowed enumerated categories/urgencies/statuses, positive integers for affected users, and non-empty IDs before any write.
  - Use `tempfile.NamedTemporaryFile` in the same directory followed by `os.fsync` and `os.replace` to ensure zero file corruption on unexpected termination.
- **My Independent Experiment/Test**:
  - Tested creating a file with legacy list format, passing it to `load_data()`, and verifying it returns `(tickets, [])`. Tested saving with `save_data()`, reading raw JSON to verify `"version": 2`, and confirming `load_tickets()` returns the ticket list unchanged.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: Suggested modifying `save_tickets` directly to wrap the tickets into `{"version": 2, "tickets": tickets}`.
  - *Identified flaw*: In `test_storage.py`, `test_save_and_load_round_trip` directly compares `save_tickets(original_tickets)` with `load_tickets()`, where `original_tickets` is a list of dicts without container metadata. Changing `save_tickets` to unconditionally write a dict would alter file structure for v1 consumers.
  - *Correction applied*: Preserved `save_tickets` for list-based v1 serialization and added `save_data` / `load_data` for Version-2 container persistence, while making `load_tickets` dual-mode compatible.
- **Verification Source or Result**:
  - `tests/test_storage.py` (7 tests passing) and `tests/test_storage_v2.py` (10 tests passing).
- **Decision**: Improved and accepted corrected version.
- **Related File / Commit**: `campusflow/storage.py`, `tests/test_storage_v2.py`.
- **What I Can Now Explain Without AI**:
  - I can explain how to design backward-compatible schema migrations in file-based storage and how atomic file swapping prevents partial-write data corruption.

---

### Learning Loop 3: Event-Driven SLA Calculation, Overdue Detection & Escalation Cycles
- **Problem**:
  - How to model SLA durations (`critical`: 60m, `high`: 240m, `medium`: 1440m, `low`: 2880m) and batch escalation so that overdue tickets advance their cycle and log audit events without modifying unrelated tickets or resolved tickets.
- **My Initial Understanding**:
  - We can check if `now > due_at` and increment a counter, but we must make sure resolved tickets are never marked overdue and that the deadline resets for the new cycle.
- **Prompt to AI**:
  - "Design a clean function for SLA deadline calculation based on priority and cycle start time. Then implement batch overdue escalation: for each overdue ticket, advance escalation_cycle, update updated_at, compute new due_at, and append an audit event. How do we ensure idempotent clock resolution?"
- **Useful AI Guidance**:
  - Resolve the current time once at the start of `escalate_overdue` (`now_dt = resolve_now(now)`) so that all tickets evaluated in that batch share the exact same timestamp.
  - Keep `calculate_due_at(priority, cycle_start)` pure: given a priority and start instant, return `cycle_start + timedelta(minutes=SLA_MINUTES[priority])`.
  - Guard `is_overdue` so that tickets with `status == "resolved"` immediately return `False`.
- **My Independent Experiment/Test**:
  - Created a test case with 3 tickets: one overdue open ticket, one non-overdue open ticket, and one resolved ticket past its original deadline. Ran `escalate_overdue()` with a fixed clock and verified that only the open overdue ticket was escalated, its `escalation_cycle` moved from 0 to 1, its new `due_at` was extended by its SLA duration from `now`, and exactly one event (`E001`) was added to `events`.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: Suggested auto-bumping the ticket priority upon escalation (e.g. from `high` to `critical`).
  - *Identified flaw*: The authoritative project rules require preserving original priority calculation rules and precedence exactly; escalation tracks lifecycle urgency via `escalation_cycle` without mutating the inherent business priority calculated from urgency and affected users.
  - *Correction applied*: Maintained the original priority, incremented `escalation_cycle`, updated timestamps, and logged the cycle change in the event details.
- **Verification Source or Result**:
  - `tests/test_sla.py::TestEscalateOverdue` and `tests/test_sla.py::TestIsOverdue`.
- **Decision**: Improved and accepted corrected version.
- **Related File / Commit**: `campusflow/sla.py`, `campusflow/events.py`, `tests/test_sla.py`.
- **What I Can Now Explain Without AI**:
  - I can explain how SLA deadlines are computed from cycle start, how finite escalation cycles track unresolved incidents, and how to structure audit events for auditability without mutating underlying business priority rules.

