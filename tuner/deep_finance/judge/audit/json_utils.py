# -*- coding: utf-8 -*-
"""JSON Utilities for Audit Grader"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_first_json_object(text: str) -> str | None:
    if not text:
        return None
    m = _JSON_RE.search(text.strip())
    if not m:
        return None
    return m.group(0)


def _repair_json(js: str) -> str:
    """
    Attempt to repair common JSON format errors:
    1. Unescape newlines within strings
    2. Fix trailing commas
    3. Fix missing commas
    4. Fix incomplete (truncated) JSON
    """

    # 1. Escape unescaped newlines within string values
    # Most common issue: LLM outputs raw newlines
    # in strings instead of \n
    def escape_newlines_in_strings(s: str) -> str:
        result = []
        in_string = False
        escape_next = False
        i = 0
        while i < len(s):
            c = s[i]
            if escape_next:
                result.append(c)
                escape_next = False
            elif c == "\\":
                result.append(c)
                escape_next = True
            elif c == '"':
                result.append(c)
                in_string = not in_string
            elif in_string and c == "\n":
                result.append("\\n")
            elif in_string and c == "\r":
                result.append("\\r")
            elif in_string and c == "\t":
                result.append("\\t")
            else:
                result.append(c)
            i += 1
        return "".join(result)

    js = escape_newlines_in_strings(js)

    # 2. Remove trailing commas: ",}" -> "}" and ",]" -> "]"
    js = re.sub(r",\s*}", "}", js)
    js = re.sub(r",\s*]", "]", js)

    # 3. Attempt to fix truncated JSON - complete missing brackets
    # Count bracket pairs
    open_braces = js.count("{")
    close_braces = js.count("}")
    open_brackets = js.count("[")
    close_brackets = js.count("]")

    # If brackets are unbalanced, try to complete them
    if open_braces > close_braces:
        # First close any unclosed strings
        # Check if we're inside a string
        in_string = False
        escape_next = False
        for c in js:
            if escape_next:
                escape_next = False
            elif c == "\\":
                escape_next = True
            elif c == '"':
                in_string = not in_string
        if in_string:
            js += '"'

        # Complete missing brackets
        js += "]" * (open_brackets - close_brackets)
        js += "}" * (open_braces - close_braces)

    return js


def strict_load_json(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    js = extract_first_json_object(text)
    if js is None:
        return None, "No JSON object found"

    # First attempt: parse directly
    try:
        obj = json.loads(js)
        if not isinstance(obj, dict):
            return None, f"Root is not dict: {type(obj)}"
        return obj, None
    except json.JSONDecodeError:
        pass  # Continue trying to repair

    # Second attempt: repair and parse
    try:
        repaired = _repair_json(js)
        obj = json.loads(repaired)
        if not isinstance(obj, dict):
            return None, f"Root is not dict: {type(obj)}"
        return obj, None
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {str(e)}"


def validate_integrity_shape(  # pylint: disable=too-many-return-statements
    obj: Dict[str, Any],
) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Validate the output structure of Evidence Logic Analyst.
    Schema:
    {
      "audit_trail": [
         {"citation_id": int, "verdict": str, ...}, ...
      ],
      "qualitative_summary": str,
      "integrity_score": float
    }
    """
    # 1. Check Top-level fields
    required_fields = ["audit_trail", "qualitative_summary", "integrity_score"]
    for f in required_fields:
        if f not in obj:
            return None, f"Missing field: {f}"

    # 2. Validate integrity_score
    try:
        score = float(obj["integrity_score"])
        if not 0.0 <= score <= 1.0:
            # Tolerance: clamp slightly out-of-range values
            score = max(0.0, min(1.0, score))
        obj["integrity_score"] = score
    except ValueError:
        return None, "integrity_score must be a float"

    # 3. Validate audit_trail
    if not isinstance(obj["audit_trail"], list):
        return None, "audit_trail must be a list"

    valid_verdicts = {
        "Supported",
        "Overstated",
        "Contradicted",
        "Hallucinated",
        "Irrelevant",
    }

    for idx, item in enumerate(obj["audit_trail"]):
        if not isinstance(item, dict):
            return None, f"audit_trail[{idx}] is not a dict"

        # Check required item fields
        if "citation_id" not in item:
            return None, f"audit_trail[{idx}] missing 'citation_id'"
        if "verdict" not in item:
            return None, f"audit_trail[{idx}] missing 'verdict'"

        # Normalize verdict
        v = str(item["verdict"]).strip()
        # Simple case-insensitive compatibility
        v_cap = v.capitalize()
        if v not in valid_verdicts and v_cap in valid_verdicts:
            item["verdict"] = v_cap
        elif v not in valid_verdicts:
            # If model outputs an unexpected verdict,
            # return error to maintain strictness
            return None, f"Invalid verdict '{v}' in item {idx}"

    return obj, None


# =============================================================================
# Trajectory Helpers
# =============================================================================


def _extract_text_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Handle OpenAI multi-part content
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text", ""))
            elif isinstance(p, str):
                parts.append(p)
        return "\n".join(parts)
    return str(content)


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S).strip()


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _extract_tool_call_json(text: str) -> str:
    # Try to extract ```json ... ```
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        return m.group(1).strip()
    # Simple fallback
    if text.strip().startswith("[") and text.strip().endswith("]"):
        return text.strip()
    return ""


def construct_reward_prompt(
    trajectory: List[Dict[str, Any]],
    template: str,
) -> str:
    """
    Extract User Query, Evidence (Tool Outputs), Final Report
    """
    user_query = ""
    evidence_parts = []
    final_report = ""

    # Helper to clean text
    def clean(c):
        return _strip_think(_extract_text_content(c))

    # 1. Identify components
    # Reverse search for Final Report
    # (Assistant message with References or TASK_COMPLETED)
    for i in range(len(trajectory) - 1, -1, -1):
        msg = trajectory[i]
        if msg.get("role") == "assistant":
            txt = clean(msg.get("content"))
            # Heuristic: long text is usually the report
            if (
                "References" in txt
                or "[TASK_COMPLETED]" in txt
                or len(txt) > 600
            ):
                final_report = _strip_markdown_fences(txt)
                break

    # Fallback: use last assistant message if no explicit report found
    if not final_report and trajectory:
        last = trajectory[-1]
        if last.get("role") == "assistant":
            final_report = _strip_markdown_fences(clean(last.get("content")))

    for idx, msg in enumerate(trajectory):
        role = msg.get("role")
        content_raw = clean(msg.get("content"))

        # User Query: First user message
        if role == "user" and not user_query:
            user_query = content_raw
            continue  # Don't treat query as evidence

        # Evidence: Tool calls and Tool outputs
        if role == "assistant":
            # Check for tool calls
            tool_json = _extract_tool_call_json(content_raw)
            if tool_json:
                evidence_parts.append(
                    f"--- Step {idx} Tool Call ---\n{tool_json}",
                )

        elif role == "tool":
            evidence_parts.append(
                f"--- Step {idx} Tool Result ---\n{content_raw}",
            )

    evidence_text = "\n\n".join(evidence_parts)

    return template.format(
        user_query=user_query,
        evidence_text=evidence_text,
        final_report=final_report,
    )
