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

## Engineer A (Theophilus Jacob / tjayokanmi) Learning Loops (Partner Record)

- **Loop 1: Input Validation and Boundary Checking in Python**
  - *Topic*: Validating non-empty strings, positive integer ranges, and tuple inclusion for category validation.
  - *Status*: (Coordinated with Engineer A; recorded in partner sprint records).

- **Loop 2: Priority Calculation Engine Design**
  - *Topic*: Sequential evaluation of compound boolean rules (urgency + affected users) with deterministic fallbacks.
  - *Status*: (Coordinated with Engineer A; recorded in partner sprint records).

- **Loop 3: Formatted String Sequential ID Generation**
  - *Topic*: Parsing max existing numeric ID and formatting with zero padding `f"T{max_id + 1:03d}"`.
  - *Status*: (Coordinated with Engineer A; recorded in partner sprint records).
