"""JSON persistence for CampusFlow tickets with atomic file replacement."""

import json
import os
import tempfile

DEFAULT_DATA_PATH = os.path.join("data", "tickets.json")


def load_tickets(filepath: str = DEFAULT_DATA_PATH) -> list[dict]:
    """Load tickets from a JSON file.

    Rules:
        - If the file does not exist, returns an empty list (permits fresh start).
        - If JSON is malformed or structure is invalid, raises ValueError.
        - Never silently replaces corrupt data with an empty list.

    Returns:
        A list of ticket dictionaries.
    """
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupted JSON in data file '{filepath}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read data file '{filepath}': {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"Corrupted data file '{filepath}': root JSON structure must be a list of tickets, found {type(data).__name__}"
        )

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Corrupted data file '{filepath}': item at index {idx} is not a valid ticket dictionary"
            )

    return data


def save_tickets(tickets: list[dict], filepath: str = DEFAULT_DATA_PATH) -> None:
    """Save tickets to a JSON file using atomic replacement.

    Atomic write process:
        1. Ensure destination directory exists.
        2. Write formatted JSON to a temporary file in the same directory.
        3. Flush and sync file descriptor to physical storage.
        4. Atomically replace the target file with the temporary file (os.replace).

    Raises:
        TypeError: If tickets is not a list.
        ValueError: If tickets contains non-dict items.
    """
    if not isinstance(tickets, list):
        raise TypeError(f"Tickets must be a list, received {type(tickets).__name__}")

    for idx, item in enumerate(tickets):
        if not isinstance(item, dict):
            raise ValueError(f"All ticket items must be dictionaries, item at index {idx} is {type(item).__name__}")

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    target_dir = directory if directory else "."

    temp_file = tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8")
    temp_path = temp_file.name
    try:
        json.dump(tickets, temp_file, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise
