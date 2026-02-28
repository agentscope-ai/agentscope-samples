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
    尝试修复常见的JSON格式错误
    1. 修复字符串中未转义的换行符
    2. 修复trailing comma
    3. 修复缺少的逗号
    4. 修复不完整的JSON（截断）
    """
    # 1. 替换字符串值中的未转义换行符
    # 这是最常见的问题：LLM在字符串中直接输出换行而非 \n
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
    # 统计括号数量
    open_braces = js.count('{')
    close_braces = js.count('}')
    open_brackets = js.count('[')
    close_brackets = js.count(']')
    
    # 如果括号不匹配，尝试补全
    if open_braces > close_braces:
        # 先关闭可能未闭合的字符串
        # 检查最后是否在字符串中
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


def strict_load_json(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    js = extract_first_json_object(text)
    if js is None:
        return None, "No JSON object found"
    
    # 第一次尝试：直接解析
    try:
        obj = json.loads(js)
        if not isinstance(obj, dict):
            return None, f"Root is not dict: {type(obj)}"
        return obj, None
    except json.JSONDecodeError:
        pass  # 继续尝试修复
    
    # 第二次尝试：修复后解析
    try:
        repaired = _repair_json(js)
        obj = json.loads(repaired)
        if not isinstance(obj, dict):
            return None, f"Root is not dict: {type(obj)}"
        return obj, None
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {str(e)}"

def validate_integrity_shape(obj: Dict[str, Any]) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    验证 Evidence Logic Analyst 的输出结构
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
        if not (0.0 <= score <= 1.0):
             # 容错：稍微越界归一化
             score = max(0.0, min(1.0, score))
        obj["integrity_score"] = score
    except ValueError:
        return None, "integrity_score must be a float"

    # 3. Validate audit_trail
    if not isinstance(obj["audit_trail"], list):
        return None, "audit_trail must be a list"

    valid_verdicts = {"Supported", "Overstated", "Contradicted", "Hallucinated", "Irrelevant"}
    
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
        # 简单的大小写兼容
        v_cap = v.capitalize()
        if v not in valid_verdicts and v_cap in valid_verdicts:
            item["verdict"] = v_cap
        elif v not in valid_verdicts:
            # 如果模型输出了奇奇怪怪的verdict，降级为Irrelevant或报错，这里选择报错以保证严谨
            return None, f"Invalid verdict '{v}' in item {idx}"

    return obj, None


# =============================================================================
# Trajectory Helpers
# =============================================================================

def _extract_text_content(content) -> str:
    if content is None: return ""
    if isinstance(content, str): return content
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
    text = re.sub(r'^```(?:markdown|md)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()

def _extract_tool_call_json(text: str) -> str:
    # 尝试提取 ```json ... ```
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text)
    if m: return m.group(1).strip()
    # 简单的 fallback
    if text.strip().startswith("[") and text.strip().endswith("]"):
        return text.strip()
    return ""

def construct_reward_prompt(trajectory: List[Dict[str, Any]], template: str) -> str:
    """
    提取 User Query, Evidence (Tool Outputs), Final Report
    """
    user_query = ""
    evidence_parts = []
    final_report = ""

    # Helper to clean text
    def clean(c): return _strip_think(_extract_text_content(c))

    # 1. Identify components
    # 倒序查找 Final Report (包含 References 或 TASK_COMPLETED 的 Assistant 消息)
    for i in range(len(trajectory) - 1, -1, -1):
        msg = trajectory[i]
        if msg.get("role") == "assistant":
            txt = clean(msg.get("content"))
            # 宽松判定：通常最后的长文本是报告
            if "References" in txt or "[TASK_COMPLETED]" in txt or len(txt) > 600:
                final_report = _strip_markdown_fences(txt)
                break
    
    # 找不到显式报告时，取最后一条 Assistant
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
            continue # 不要把 query 当作 evidence

        # Evidence: Tool calls and Tool outputs
        if role == "assistant":
            # Check for tool calls
            tool_json = _extract_tool_call_json(content_raw)
            if tool_json:
                evidence_parts.append(f"--- Step {idx} Tool Call ---\n{tool_json}")
        
        elif role == "tool":
            evidence_parts.append(f"--- Step {idx} Tool Result ---\n{content_raw}")

    evidence_text = "\n\n".join(evidence_parts)

    return template.format(
        user_query=user_query,
        evidence_text=evidence_text,
        final_report=final_report
    )