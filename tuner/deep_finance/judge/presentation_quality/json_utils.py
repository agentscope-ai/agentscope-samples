from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_first_json_object(text: str) -> str | None:
    """
    Best-effort: extract the first {...} block.
    If none found, return None.
    """
    if not text:
        return None
    m = _JSON_RE.search(text.strip())
    if not m:
        return None
    return m.group(0)


def strict_load_json(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Return (obj, error). Any parse failure => (None, error_msg)
    """
    js = extract_first_json_object(text)
    if js is None:
        return None, "No JSON object found in model output"
    try:
        obj = json.loads(js)
        if not isinstance(obj, dict):
            return None, f"Top-level JSON is not an object: {type(obj).__name__}"
        return obj, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def get_bool_pass(item: Any) -> bool:
    if isinstance(item, dict):
        v = item.get("pass")
    else:
        v = item
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "y"}
    return False


def get_score(item: Any) -> int:
    """
    Extract numeric score (1, 3, 5) from item.
    Returns 1 as default if invalid.
    """
    if isinstance(item, dict):
        v = item.get("score")
    else:
        v = item
    if isinstance(v, (int, float)):
        v = int(v)
        if v in (1, 3, 5):
            return v
        # clamp to valid range
        if v <= 1:
            return 1
        if v >= 5:
            return 5
        return 3
    return 1


def get_note(item: Any) -> str:
    if isinstance(item, dict):
        note = item.get("note", "")
    else:
        note = ""
    note = "" if note is None else str(note)
    note = note.strip()
    # 最多给点余量，避免reason爆长
    return note[:120]


def validate_shape(obj: Dict[str, Any]) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Ensure required sections exist and are dicts; ensure top_fixes is list or str.
    If missing required field => error.
    """
    for sec in ("scan", "structuring", "editorial"):
        if sec not in obj:
            return None, f"Missing field: {sec}"
        if not isinstance(obj[sec], dict):
            return None, f"Field '{sec}' is not an object"
    if "top_fixes" not in obj:
        return None, "Missing field: top_fixes"
    # normalize top_fixes
    tf = obj.get("top_fixes")
    if isinstance(tf, list):
        obj["top_fixes"] = [str(x) for x in tf][:3]
    elif tf is None:
        obj["top_fixes"] = []
    else:
        obj["top_fixes"] = [str(tf)][:3]
    return obj, None
