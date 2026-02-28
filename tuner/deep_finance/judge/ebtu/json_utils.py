# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple


# =============================================================================
# JSON Repair Helper
# =============================================================================

def _repair_json(js: str) -> str:
    """
    尝试修复常见的JSON格式错误
    1. 修复字符串中未转义的换行符
    2. 修复trailing comma
    3. 修复不完整的JSON（截断）
    """
    # 1. 替换字符串值中的未转义换行符
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
            elif c == '\\':
                result.append(c)
                escape_next = True
            elif c == '"':
                result.append(c)
                in_string = not in_string
            elif in_string and c == '\n':
                result.append('\\n')
            elif in_string and c == '\r':
                result.append('\\r')
            elif in_string and c == '\t':
                result.append('\\t')
            else:
                result.append(c)
            i += 1
        return ''.join(result)
    
    js = escape_newlines_in_strings(js)
    
    # 2. 移除trailing comma: ",}" -> "}" 和 ",]" -> "]"
    js = re.sub(r',\s*}', '}', js)
    js = re.sub(r',\s*]', ']', js)
    
    # 3. 尝试修复截断的JSON - 补全缺失的括号
    open_braces = js.count('{')
    close_braces = js.count('}')
    open_brackets = js.count('[')
    close_brackets = js.count(']')
    
    if open_braces > close_braces:
        # 先关闭可能未闭合的字符串
        in_string = False
        escape_next = False
        for c in js:
            if escape_next:
                escape_next = False
            elif c == '\\':
                escape_next = True
            elif c == '"':
                in_string = not in_string
        if in_string:
            js += '"'
        
        # 补全缺失的括号
        js += ']' * (open_brackets - close_brackets)
        js += '}' * (open_braces - close_braces)
    
    return js


def strict_load_json(text: str) -> Dict[str, Any]:
    """Parse a JSON object from model output; extract first {...} block if needed. 带容错修复。"""
    text = (text or "").strip()
    
    # 第一次尝试：直接解析
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 尝试提取 {...} 片段
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        # 第二次尝试：直接解析提取的片段
        try:
            obj = json.loads(snippet)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        
        # 第三次尝试：修复后解析
        try:
            repaired = _repair_json(snippet)
            obj = json.loads(repaired)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise ValueError("Invalid JSON output")


def _clip(s: str, n: int) -> str:
    s = s or ""
    s = s.replace("\u0000", "")
    return s[:n]


def _as_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return int(x)
        if isinstance(x, (int, float)):
            return int(x)
        if isinstance(x, str) and x.strip():
            return int(float(x.strip()))
    except Exception:
        return default
    return default


def _as_list_str(x: Any, max_items: int = 10, max_len: int = 60) -> List[str]:
    if not isinstance(x, list):
        return []
    out: List[str] = []
    for item in x[:max_items]:
        if isinstance(item, str):
            out.append(_clip(item, max_len))
        else:
            out.append(_clip(str(item), max_len))
    return out


def validate_shape(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize model output for EBTU.

    Returns:
      {"units": [...], "stats": {...}, "examples": {...}}
    """
    if not isinstance(obj, dict):
        raise ValueError("Output is not a JSON object")

    units_raw = obj.get("units", [])
    if not isinstance(units_raw, list):
        units_raw = []

    units: List[Dict[str, Any]] = []
    for u in units_raw[:30]:
        if not isinstance(u, dict):
            continue

        claim = _clip(str(u.get("claim", "")), 280)
        hardness = _clip(str(u.get("hardness", "hard")), 8)
        if hardness not in {"hard", "soft"}:
            hardness = "hard"

        utype = _clip(str(u.get("type", "other")), 24)

        sig = u.get("signature", {})
        if not isinstance(sig, dict):
            sig = {}
        entities = _as_list_str(sig.get("entities", []), max_items=10, max_len=60)
        numbers = _as_list_str(sig.get("numbers", []), max_items=10, max_len=40)
        times = _as_list_str(sig.get("times", []), max_items=10, max_len=40)

        ev = u.get("evidence", {})
        if not isinstance(ev, dict):
            ev = {}
        anchors_raw = ev.get("anchors", [])
        anchors: List[Dict[str, Any]] = []
        if isinstance(anchors_raw, list):
            for a in anchors_raw[:2]:
                if not isinstance(a, dict):
                    continue
                step = _as_int(a.get("step", -1), default=-1)
                quote = _clip(str(a.get("quote", "")), 120)
                if step >= 0 and quote:
                    anchors.append({"step": step, "quote": quote})
        anchor_note = _clip(str(ev.get("anchor_note", "")), 60)

        ver = u.get("verification", {})
        if not isinstance(ver, dict):
            ver = {}

        verdict = _clip(str(ver.get("verdict", "unclear")), 20)
        if verdict not in {"supported", "contradicted", "no_evidence", "speculative_ok", "unclear"}:
            verdict = "unclear"

        issue = _clip(str(ver.get("issue", "none")), 20)
        allowed_issues = {
            "none", "entity_mismatch", "time_mismatch", "value_mismatch", "scope_mismatch",
            "logic_leap", "over_precision", "missing_anchor"
        }
        if issue not in allowed_issues:
            issue = "none"

        note = _clip(str(ver.get("note", "")), 80)

        units.append({
            "claim": claim,
            "hardness": hardness,
            "type": utype,
            "signature": {"entities": entities, "numbers": numbers, "times": times},
            "evidence": {"anchors": anchors, "anchor_note": anchor_note},
            "verification": {"verdict": verdict, "issue": issue, "note": note},
        })

    # Recompute counts (anti-gaming)
    verdict_counts = {k: 0 for k in ["supported", "contradicted", "no_evidence", "speculative_ok", "unclear"]}
    hard_units = 0
    anchored_hard_units = 0
    misattrib = 0
    for u in units:
        v = u["verification"]["verdict"]
        verdict_counts[v] += 1
        if u["hardness"] == "hard":
            hard_units += 1
            if u["evidence"]["anchors"]:
                anchored_hard_units += 1
                if v != "supported":
                    misattrib += 1

    stats_raw = obj.get("stats", {})
    if not isinstance(stats_raw, dict):
        stats_raw = {}
    report_digit_date_tokens = max(0, _as_int(stats_raw.get("report_digit_date_tokens", 0), default=0))
    covered_digit_date_tokens = max(0, _as_int(stats_raw.get("covered_digit_date_tokens", 0), default=0))

    stats = {
        "total_units": len(units),
        "hard_units": hard_units,
        "supported": verdict_counts["supported"],
        "contradicted": verdict_counts["contradicted"],
        "no_evidence": verdict_counts["no_evidence"],
        "speculative_ok": verdict_counts["speculative_ok"],
        "unclear": verdict_counts["unclear"],
        "report_digit_date_tokens": report_digit_date_tokens,
        "covered_digit_date_tokens": covered_digit_date_tokens,
        "anchored_hard_units": anchored_hard_units,
        "misattrib": misattrib,
    }

    examples_raw = obj.get("examples", {})
    if not isinstance(examples_raw, dict):
        examples_raw = {}

    def _norm_list(x: Any, max_items: int = 2) -> List[Dict[str, Any]]:
        if not isinstance(x, list):
            return []
        out: List[Dict[str, Any]] = []
        for it in x[:max_items]:
            if isinstance(it, dict):
                out.append({k: _clip(str(v), 160) for k, v in list(it.items())[:4]})
            elif isinstance(it, str):
                out.append({"text": _clip(it, 160)})
        return out

    examples = {
        "best_supported": _norm_list(examples_raw.get("best_supported", []), 2),
        "worst_failed": _norm_list(examples_raw.get("worst_failed", []), 2),
    }

    return {"units": units, "stats": stats, "examples": examples}


def coerce_to_messages_list(traj: Any) -> List[Dict[str, Any]]:
    """Accept list[dict], list[list[dict]], or dict wrapper."""
    if traj is None:
        return []
    if isinstance(traj, dict):
        for key in ("traj", "messages", "conversation", "steps"):
            if key in traj:
                return coerce_to_messages_list(traj[key])
        return []
    if isinstance(traj, list):
        if not traj:
            return []
        if isinstance(traj[0], list):
            for inner in traj:
                if isinstance(inner, list) and inner and isinstance(inner[0], dict):
                    return inner
            return []
        if isinstance(traj[0], dict):
            return traj
    return []


def _extract_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join([p for p in parts if p])
    return str(content)


def strip_references(markdown: str) -> str:
    if not isinstance(markdown, str):
        return ""
    m = re.search(r"\n#+\s*References\b", markdown, flags=re.IGNORECASE)
    if m:
        return markdown[: m.start()].strip()
    return markdown.strip()


def count_digit_tokens(text: str) -> int:
    if not text:
        return 0
    pats = [
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        r"\b\d+(?:\.\d+)?%?\b",
    ]
    tokens: List[str] = []
    for p in pats:
        tokens.extend(re.findall(p, text))
    return len(tokens)


def _strip_think(text: str) -> str:
    """去除 <think>...</think> 标签"""
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S).strip()


def _looks_like_tool_result(text: str) -> bool:
    """判断是否为工具返回结果"""
    t = (text or "").strip()
    if t.startswith("Tool:") or t.startswith("Result:"):
        return True
    if t.startswith("{") and ("query" in t) and ("search_results" in t or "response_content" in t):
        return True
    if ("股票代码 |" in t) or ("单位：" in t) or t.startswith("### "):
        return True
    return False


def _is_probably_final_report(text: str) -> bool:
    """判断是否为最终报告"""
    if not text:
        return False
    t = text.strip()
    # 放宽条件：任一条件满足即可
    if "## References" in t or "[TASK_COMPLETED]" in t:
        return True
    if t.lstrip().startswith("# "):
        return True
    # 兼容原有逻辑
    has_markdown = ("#" in t) or ("|---" in t) or ("## " in t)
    has_refs = re.search(r"#+\s*References\b", t, flags=re.IGNORECASE) is not None
    return has_markdown and has_refs


def _extract_tool_calls_and_results(trajectory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for i, msg in enumerate(trajectory):
        role = msg.get("role", "")
        content = _extract_text_content(msg.get("content", ""))
        if role == "assistant":
            if "```json" in content and ("tool_name" in content or "tool_args" in content):
                items.append({"step": i, "kind": "tool_call", "text": content})
        elif role == "tool":
            items.append({"step": i, "kind": "tool_result", "text": content})
    return items


def construct_reward_prompt(trajectory: List[Dict[str, Any]], user_prompt_template: str) -> str:
    trajectory = coerce_to_messages_list(trajectory)

    # 提取 user_query（第一个非工具结果的 user 消息）
    user_query = ""
    for msg in trajectory:
        if msg.get("role") == "user":
            raw = _extract_text_content(msg.get("content", ""))
            if not _looks_like_tool_result(raw):
                user_query = _strip_think(raw)
                break

    # 提取 final_report（从后往前找第一个符合条件的 assistant 消息）
    final_report = ""
    for msg in reversed(trajectory):
        if msg.get("role") == "assistant":
            raw = _extract_text_content(msg.get("content", ""))
            t = _strip_think(raw)
            if _is_probably_final_report(t):
                final_report = t
                break
    if not final_report:
        for msg in reversed(trajectory):
            if msg.get("role") == "assistant":
                raw = _extract_text_content(msg.get("content", ""))
                final_report = _strip_think(raw)
                break

    evidence_items = _extract_tool_calls_and_results(trajectory)
    evidence_lines: List[str] = []
    for it in evidence_items:
        step = it["step"]
        prefix = "CALL" if it["kind"] == "tool_call" else "RESULT"
        evidence_lines.append(f"[{prefix} step={step}]\n{it['text']}".strip())
    evidence_text = "\n\n".join(evidence_lines).strip()

    return user_prompt_template.format(
        user_query=user_query,
        evidence_text=evidence_text,
        final_report=final_report,
    )


def construct_ebtu_prompt(
    trajectory: List[Dict[str, Any]],
    user_prompt_template: str,
) -> Tuple[str, str]:
    """
    Returns:
      - user_prompt (for judge)
      - report_plain (final report without References) for deterministic coverage checks
    """
    user_prompt = construct_reward_prompt(trajectory, user_prompt_template)

    report_plain = ""
    for marker in ("\n## Report\n", "\n## AI Report\n"):
        if marker in user_prompt:
            report_plain = user_prompt.split(marker, 1)[1]
            break
    if not report_plain:
        report_plain = user_prompt

    report_plain = strip_references(report_plain)
    return user_prompt, report_plain
