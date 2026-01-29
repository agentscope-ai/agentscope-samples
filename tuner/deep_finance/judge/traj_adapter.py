from __future__ import annotations

from typing import Any, Dict, List, Tuple


def extract_text_content(content: Any) -> str:
    """Extract plain text from common message schemas."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: List[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts)
    return str(content)


def normalize_traj(traj: Any) -> List[Dict[str, Any]]:
    """
    Accept common traj shapes:
      - list[{"role":..., "content":...}, ...]
      - {"trajectory": [...]}
      - {"messages": [...]}
    """
    if isinstance(traj, list):
        return traj
    if isinstance(traj, dict):
        if isinstance(traj.get("trajectory"), list):
            return traj["trajectory"]
        if isinstance(traj.get("messages"), list):
            return traj["messages"]
    return []


def infer_user_query(trajectory: List[Dict[str, Any]]) -> str:
    for step in trajectory:
        if step.get("role") == "user":
            txt = extract_text_content(step.get("content"))
            if txt.strip():
                return txt.strip()
    return ""


def find_final_report(trajectory: List[Dict[str, Any]]) -> str:
    """
    Heuristic: last assistant long text or markdown-like content.
    """
    for step in reversed(trajectory):
        if step.get("role") == "assistant":
            txt = extract_text_content(step.get("content", ""))
            if len(txt) > 120 or "#" in txt:
                return txt
    return ""



