from datetime import datetime, timezone
from typing import Any


def _to_iso_date(value: Any) -> str:
    """Convert a timestamp value to an ISO date string (YYYY-MM-DD).

    Handles int/float timestamps, datetime objects, and falls back to str().
    """
    if value is None:
        return ""
    try:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    return str(value)
