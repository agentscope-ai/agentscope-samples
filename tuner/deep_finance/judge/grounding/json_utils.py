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
    验证 grounding JSON 结构
    
    必需字段:
    - total_key_facts: int
    - cited_key_facts: int
    - missing_count: int
    - fake_count: int
    - good_citations: list
    - invalid_reference_nums: list
    """
    # 必需的 int 字段
    int_fields = ["total_key_facts", "cited_key_facts", "missing_count", "fake_count"]
    for field in int_fields:
        if field not in obj:
            return None, f"Missing field: {field}"
        val = obj[field]
        # 尝试转换为 int
        if isinstance(val, (int, float)):
            obj[field] = int(val)
        elif isinstance(val, str) and val.isdigit():
            obj[field] = int(val)
        elif not isinstance(val, int):
            return None, f"Field '{field}' must be int, got {type(val).__name__}"
    
    # good_citations 必须是 list
    if "good_citations" not in obj:
        obj["good_citations"] = []
    elif not isinstance(obj["good_citations"], list):
        obj["good_citations"] = []
    else:
        # 确保每个元素是字符串，最多保留 2 条
        obj["good_citations"] = [str(x) for x in obj["good_citations"][:2]]
    
    # invalid_reference_nums 必须是 list
    if "invalid_reference_nums" not in obj:
        obj["invalid_reference_nums"] = []
    elif not isinstance(obj["invalid_reference_nums"], list):
        obj["invalid_reference_nums"] = []
    else:
        # 确保每个元素是 int，最多保留 5 个
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
# Trajectory 处理辅助函数
# =============================================================================

def _extract_text_content(content) -> str:
    """统一提取纯文本内容"""
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
    """去除 <think>...</think> 标签"""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S).strip()


def _strip_markdown_fences(text: str) -> str:
    """
    清理 markdown 代码块标记
    - 移除开头的 ```markdown / ```md / ``` 等
    - 移除结尾的 ```
    """
    text = text.strip()
    # 移除开头的 ```xxx
    text = re.sub(r'^```(?:markdown|md)?\s*\n?', '', text, flags=re.IGNORECASE)
    # 移除结尾的 ```
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def _normalize_traj(trajectory):
    """兼容 [[...]] 格式"""
    if isinstance(trajectory, list) and trajectory and isinstance(trajectory[0], list):
        return trajectory[0]
    return trajectory


def _extract_tool_call_json(text: str) -> str:
    """提取工具调用 JSON"""
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        return m.group(1).strip()
    l, r = text.find("["), text.rfind("]")
    if l != -1 and r != -1 and r > l:
        cand = text[l:r+1].strip()
        if ("tool_name" in cand) and ("tool_args" in cand):
            return cand
    return ""


def _looks_like_tool_result(text: str) -> bool:
    """判断是否为工具返回结果"""
    t = text.strip()
    if t.startswith("Tool:") or t.startswith("Result:"):
        return True
    if t.startswith("{") and ("query" in t) and ("search_results" in t or "response_content" in t):
        return True
    if ("股票代码 |" in t) or ("单位：" in t) or t.startswith("### "):
        return True
    return False


def _is_probably_final_report(text: str) -> bool:
    """判断是否为最终报告"""
    t = text.strip()
    return ("## References" in t) or ("[TASK_COMPLETED]" in t) or t.lstrip().startswith("# ")


def construct_reward_prompt(trajectory: List[Dict[str, Any]], user_prompt_template: str) -> str:
    """
    从 trajectory 构建 reward prompt
    
    Args:
        trajectory: 对话轨迹 [{"role": ..., "content": ...}, ...]
        
    Returns:
        构建好的 user prompt 字符串
    """
    traj = _normalize_traj(trajectory)
    if not traj:
        traj = []

    user_query = ""
    tool_calls: List[str] = []
    evidence: List[str] = []
    final_report = ""

    # 找到 final report（从后往前找第一个符合条件的 assistant 消息）
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
                final_report = _strip_think(_extract_text_content(traj[i].get("content")))
                break

    # 清理 markdown 代码块标记
    final_report = _strip_markdown_fences(final_report)

    # 遍历提取 user_query, tool_calls, evidence
    for idx, step in enumerate(traj):
        role = step.get("role")
        raw = _extract_text_content(step.get("content"))
        txt = _strip_think(raw)
        if not raw:
            continue

        if role == "user" and not user_query and (not _looks_like_tool_result(raw)):
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
                # query 之后的用户补充也保留为 evidence
                if user_query:
                    evidence.append(f"[Step {idx}] EVIDENCE_USER_CONTEXT:\n{txt}")

    evidence_text = "\n\n".join(tool_calls + evidence)

    return user_prompt_template.format(
        user_query=user_query,
        evidence_text=evidence_text,
        final_report=final_report
    ).strip()
