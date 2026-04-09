# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

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
            return (
                None,
                f"Top-level JSON is not an object: {type(obj).__name__}",
            )
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


def get_note(item: Any) -> str:
    if isinstance(item, dict):
        note = item.get("note", "")
    else:
        note = ""
    note = "" if note is None else str(note)
    note = note.strip()
    # Truncate to avoid overly long reason strings
    return note[:120]


def validate_shape(
    obj: Dict[str, Any],
) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Validate grounding JSON structure.

    Required fields:
    - total_key_facts: int
    - cited_key_facts: int
    - missing_count: int
    - fake_count: int
    - good_citations: list
    - invalid_reference_nums: list
    """
    # Required int fields
    int_fields = [
        "total_key_facts",
        "cited_key_facts",
        "missing_count",
        "fake_count",
    ]
    for field in int_fields:
        if field not in obj:
            return None, f"Missing field: {field}"
        val = obj[field]
        # Try to convert to int
        if isinstance(val, (int, float)):
            obj[field] = int(val)
        elif isinstance(val, str) and val.isdigit():
            obj[field] = int(val)
        elif not isinstance(val, int):
            return (
                None,
                f"Field '{field}' must be int, got {type(val).__name__}",
            )

    # good_citations must be a list
    if "good_citations" not in obj:
        obj["good_citations"] = []
    elif not isinstance(obj["good_citations"], list):
        obj["good_citations"] = []
    else:
        # Ensure each element is a string, keep at most 2
        obj["good_citations"] = [str(x) for x in obj["good_citations"][:2]]

    # invalid_reference_nums must be a list
    if "invalid_reference_nums" not in obj:
        obj["invalid_reference_nums"] = []
    elif not isinstance(obj["invalid_reference_nums"], list):
        obj["invalid_reference_nums"] = []
    else:
        # Ensure each element is int, keep at most 5
        nums = []
        for x in obj["invalid_reference_nums"][:5]:
            if isinstance(x, int):
                nums.append(x)
            elif isinstance(x, (float, str)):
                try:
                    nums.append(int(x))
                except ValueError:
                    pass
        obj["invalid_reference_nums"] = sorted(nums)

    return obj, None


# =============================================================================
# Trajectory Processing Helpers
# =============================================================================


def _extract_text_content(content) -> str:
    """Extract plain text content."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                out.append(item.get("text", ""))
            elif isinstance(item, str):
                out.append(item)
        return "\n".join(out)
    return str(content)


def _strip_think(text: str) -> str:
    """Strip <think>...</think> tags."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S).strip()


def _strip_markdown_fences(text: str) -> str:
    """
    Strip markdown code block markers.
    - Remove leading ```markdown / ```md / ``` etc.
    - Remove trailing ```
    """
    text = text.strip()
    # Remove leading ```xxx
    text = re.sub(r"^```(?:markdown|md)?\s*\n?", "", text, flags=re.IGNORECASE)
    # Remove trailing ```
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _normalize_traj(trajectory):
    """Compatible with [[...]] format."""
    if (
        isinstance(trajectory, list)
        and trajectory
        and isinstance(trajectory[0], list)
    ):
        return trajectory[0]
    return trajectory


def _extract_tool_call_json(text: str) -> str:
    """Extract tool call JSON."""
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        return m.group(1).strip()
    l, r = text.find("["), text.rfind("]")
    if l != -1 and r != -1 and r > l:
        cand = text[l : r + 1].strip()
        if ("tool_name" in cand) and ("tool_args" in cand):
            return cand
    return ""


def _looks_like_tool_result(text: str) -> bool:
    """Check if text looks like a tool result."""
    t = text.strip()
    if t.startswith("Tool:") or t.startswith("Result:"):
        return True
    if (
        t.startswith("{")
        and ("query" in t)
        and ("search_results" in t or "response_content" in t)
    ):
        return True
    if ("股票代码 |" in t) or ("单位：" in t) or t.startswith("### "):
        return True
    return False


def _is_probably_final_report(text: str) -> bool:
    """Check if text is likely the final report."""
    t = text.strip()
    return (
        ("## References" in t)
        or ("[TASK_COMPLETED]" in t)
        or t.lstrip().startswith("# ")
    )


def construct_reward_prompt(
    trajectory: List[Dict[str, Any]], user_prompt_template: str
) -> str:
    """
    Build reward prompt from trajectory.

    Args:
        trajectory: Conversation trajectory [{"role": ..., "content": ...}, ...]

    Returns:
        Constructed user prompt string
    """
    traj = _normalize_traj(trajectory)
    if not traj:
        traj = []

    user_query = ""
    tool_calls: List[str] = []
    evidence: List[str] = []
    final_report = ""

    # Find final report (reverse search for first qualifying assistant message)
    for i in range(len(traj) - 1, -1, -1):
        step = traj[i]
        if step.get("role") == "assistant":
            txt = _strip_think(_extract_text_content(step.get("content")))
            if _is_probably_final_report(txt):
                final_report = txt
                break
    if not final_report:
        for i in range(len(traj) - 1, -1, -1):
            if traj[i].get("role") == "assistant":
                final_report = _strip_think(
                    _extract_text_content(traj[i].get("content"))
                )
                break

    # Clean markdown code block markers
    final_report = _strip_markdown_fences(final_report)

    # Iterate to extract user_query, tool_calls, evidence
    for idx, step in enumerate(traj):
        role = step.get("role")
        raw = _extract_text_content(step.get("content"))
        txt = _strip_think(raw)
        if not raw:
            continue

        if (
            role == "user"
            and not user_query
            and (not _looks_like_tool_result(raw))
        ):
            user_query = txt
            continue

        if role == "assistant":
            call_json = _extract_tool_call_json(raw)
            if call_json:
                tool_calls.append(f"[Step {idx}] TOOL_CALL:\n{call_json}")

        if role in ("tool", "user"):
            if _looks_like_tool_result(raw):
                evidence.append(f"[Step {idx}] EVIDENCE_TOOL_RESULT:\n{raw}")
            else:
                # Additional user context after query is also kept as evidence
                if user_query:
                    evidence.append(
                        f"[Step {idx}] EVIDENCE_USER_CONTEXT:\n{txt}"
                    )

    evidence_text = "\n\n".join(tool_calls + evidence)

    return user_prompt_template.format(
        user_query=user_query,
        evidence_text=evidence_text,
        final_report=final_report,
    ).strip()
