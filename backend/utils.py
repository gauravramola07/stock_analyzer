from datetime import datetime, timezone
from typing import Any
import math


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


def clean_float(val: Any, default: Any = 0.0) -> Any:
    """Safely convert a value to float, replacing NaN/Inf with default."""
    if val is None:
        return default
    try:
        fval = float(val)
        if not math.isfinite(fval):
            return default
        return fval
    except (ValueError, TypeError):
        return default


def clean_json_data(data: Any) -> Any:
    """Recursively clean dictionaries, lists, and floats for JSON compliance."""
    if isinstance(data, dict):
        return {k: clean_json_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_json_data(v) for v in data]
    elif isinstance(data, float):
        if not math.isfinite(data):
            return None
        return data
    return data

