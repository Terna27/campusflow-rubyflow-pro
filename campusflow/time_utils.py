"""Deterministic UTC time handling and validation for CampusFlow."""

from datetime import datetime, timezone, timedelta
from typing import Union


class UTCTimestamp(str):
    """String subclass representing an ISO-8601 UTC timestamp.
    
    Behaves as a standard string for serialization, hashing, and string operations,
    while allowing direct equality comparison with timezone-aware datetime objects.
    """

    def __eq__(self, other: object) -> bool:
        if isinstance(other, datetime):
            try:
                self_dt = parse_utc_iso(self)
                return self_dt == other
            except Exception:
                return False
        return super().__eq__(other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    @property
    def as_datetime(self) -> datetime:
        """Return the timezone-aware datetime representation in UTC."""
        return parse_utc_iso(self)


def parse_utc_iso(ts: Union[str, datetime]) -> datetime:
    """Parse an ISO-8601 timestamp string or datetime into a timezone-aware UTC datetime.

    Rules:
        - Rejects naive datetime objects with ValueError.
        - Rejects naive timestamp strings lacking explicit timezone offsets with ValueError.
        - Rejects invalid formats or non-date values with ValueError.
        - Converts all timezone-aware inputs into UTC.

    Returns:
        A timezone-aware datetime with tzinfo=timezone.utc.
    """
    if isinstance(ts, datetime):
        if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
            raise ValueError(f"Naive datetime rejected: '{ts}'. Timezone-aware datetime required.")
        return ts.astimezone(timezone.utc)

    if not isinstance(ts, str):
        raise TypeError(f"Timestamp must be a string or datetime, received {type(ts).__name__}")

    cleaned = ts.strip()
    if not cleaned:
        raise ValueError("Timestamp string cannot be empty or whitespace only.")

    try:
        # datetime.fromisoformat parses ISO-8601 strings (including 'Z' in Python 3.11+)
        # For universal robustness, replace trailing 'Z' or 'z' with '+00:00'
        iso_str = cleaned
        if iso_str.endswith("Z") or iso_str.endswith("z"):
            iso_str = iso_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_str)
    except Exception as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp format: '{cleaned}'") from exc

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(
            f"Naive timestamp rejected: '{cleaned}'. Explicit timezone offset (e.g. 'Z' or '+00:00') required."
        )

    return dt.astimezone(timezone.utc)


def format_utc_iso(dt: Union[datetime, str]) -> UTCTimestamp:
    """Format a timezone-aware datetime or ISO string as a canonical ISO-8601 UTC string.

    Format: YYYY-MM-DDTHH:MM:SSZ (or with microseconds if present).
    """
    parsed_dt = parse_utc_iso(dt)
    # Produce clean UTC ISO string ending in 'Z'
    iso = parsed_dt.isoformat()
    if iso.endswith("+00:00"):
        iso = iso[:-6] + "Z"
    return UTCTimestamp(iso)


def resolve_now(now: Union[datetime, str, None] = None) -> datetime:
    """Resolve an optional injected clock to a timezone-aware UTC datetime.

    If now is None, resolves the system UTC clock once per operation.
    If now is provided, validates and normalizes to UTC.
    """
    if now is None:
        return datetime.now(timezone.utc)
    return parse_utc_iso(now)
