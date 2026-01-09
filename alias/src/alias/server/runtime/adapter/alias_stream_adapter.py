# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

from agentscope_runtime.engine.helpers.agent_api_builder import ResponseBuilder
from agentscope_runtime.engine.schemas.agent_schemas import (
    Content,
    DataContent,
    FunctionCall,
    FunctionCallOutput,
    Message,
    MessageType,
)


def _is_plan_confirmation_prompt(output_obj: Any) -> bool:
    """
    Check whether the tool result is prompting the user to type `continue`.
    """
    text = ""
    if isinstance(output_obj, str):
        text = output_obj
    elif isinstance(output_obj, list):
        parts = []
        for o in output_obj:
            if isinstance(o, dict) and o.get("type") == "text":
                parts.append(o.get("text") or "")
            else:
                parts.append(str(o))
        text = "\n".join(parts)
    elif isinstance(output_obj, dict):
        text = json.dumps(output_obj, ensure_ascii=False, default=str)

    t = (text or "").lower()
    return (
        'type "continue"' in t
        or "type 'continue'" in t
        or "waiting for the user to confirm" in t
        or "waiting for user to confirm" in t
    )


def _extract_prompt_text(output_obj: Any) -> str:
    """Extract prompt text for rendering as a normal assistant message."""
    if isinstance(output_obj, str):
        return output_obj
    if isinstance(output_obj, list):
        parts = []
        for o in output_obj:
            if isinstance(o, dict) and o.get("type") == "text":
                parts.append(o.get("text") or "")
        if parts:
            return "\n".join(parts)
        return str(output_obj)
    return str(output_obj)


def _safe_json_loads(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _json_dumps_always(obj: Any) -> str:
    """Always return a valid JSON string representation."""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps(str(obj), ensure_ascii=False)


def _extract_alias_messages(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = chunk.get("data") or {}
    msgs = data.get("messages") or []
    return [m for m in msgs if isinstance(m, dict)]


def _extract_item_fields(
    item: Dict[str, Any],
) -> Tuple[str, str, str, Dict[str, Any]]:
    alias_item_id = str(item.get("id") or "")
    inner = item.get("message") or {}
    alias_type = str(inner.get("type") or "response")
    alias_status = str(inner.get("status") or "running")
    return alias_item_id, alias_type, alias_status, inner


def _compute_delta(prev: str, curr: str) -> str:
    if not curr:
        return ""
    if prev and curr.startswith(prev):
        return curr[len(prev) :]
    return curr


def _normalize_call_id(inner: Dict[str, Any], alias_item_id: str) -> str:
    tcid = inner.get("tool_call_id") or inner.get("tool_callId")
    if tcid:
        return str(tcid)

    content = inner.get("content")
    if isinstance(content, str) and content:
        parsed = _safe_json_loads(content)
        if (
            isinstance(parsed, list)
            and parsed
            and isinstance(parsed[0], dict)
            and parsed[0].get("id")
        ):
            return str(parsed[0]["id"])
        if isinstance(parsed, dict) and parsed.get("id"):
            return str(parsed["id"])

    tool_name = inner.get("tool_name") or "tool"
    return f"call_{tool_name}_{alias_item_id or 'unknown'}"


def _parse_tool_use(
    inner: Dict[str, Any],
    alias_item_id: str,
) -> Tuple[str, str, Dict[str, Any]]:
    call_id = _normalize_call_id(inner, alias_item_id)
    tool_name = inner.get("tool_name")
    args: Dict[str, Any] = (
        inner.get("arguments")
        if isinstance(inner.get("arguments"), dict)
        else {}
    )

    content = inner.get("content")
    parsed = _safe_json_loads(content) if isinstance(content, str) else None
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        tool_name = parsed[0].get("name") or tool_name
        if isinstance(parsed[0].get("input"), dict):
            args = parsed[0]["input"]
    elif isinstance(parsed, dict):
        tool_name = parsed.get("name") or tool_name
        if isinstance(parsed.get("input"), dict):
            args = parsed["input"]

    return call_id, str(tool_name or "tool"), args


def _parse_tool_result(
    inner: Dict[str, Any],
    alias_item_id: str,
) -> Tuple[str, str, Any]:
    call_id = _normalize_call_id(inner, alias_item_id)
    tool_name = inner.get("tool_name")

    content = inner.get("content")
    parsed = _safe_json_loads(content) if isinstance(content, str) else None

    output_obj: Any = None
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        tool_name = parsed[0].get("name") or tool_name
        output_obj = parsed[0].get("output")
    elif isinstance(parsed, dict):
        tool_name = parsed.get("name") or tool_name
        output_obj = parsed.get("output")
    else:
        output_obj = content if content is not None else ""

    return call_id, str(tool_name or "tool"), output_obj


@dataclass
class _TextMsgState:
    mb: Any
    cb: Any
    last_text: str = ""


async def adapt_alias_message_stream(
    source_stream: AsyncIterator[Dict[str, Any]],
) -> AsyncIterator[Union[Message, Content]]:
    # pylint: disable=too-many-branches,too-many-statements
    rb = ResponseBuilder()

    text_states: Dict[str, _TextMsgState] = {}
    seen_tool_use: set[str] = set()
    seen_tool_result: set[str] = set()

    def _text_key(
        chunk: Dict[str, Any],
        alias_item_id: str,
        alias_type: str,
    ) -> str:
        return alias_item_id or f"{chunk.get('message_id')}::{alias_type}"

    async for chunk in source_stream:
        if not isinstance(chunk, dict):
            k = "non_dict"
            if k not in text_states:
                mb = rb.create_message_builder(
                    message_type=MessageType.MESSAGE,
                    role="assistant",
                )
                yield mb.get_message_data()
                cb = mb.create_content_builder(content_type="text")
                text_states[k] = _TextMsgState(mb=mb, cb=cb, last_text="")
            st = text_states[k]
            curr = st.last_text + str(chunk)
            delta = _compute_delta(st.last_text, curr)
            st.last_text = curr
            if delta:
                yield st.cb.add_text_delta(delta)
            continue

        if "error" in chunk:
            mb = rb.create_message_builder(
                message_type=MessageType.MESSAGE,
                role="assistant",
            )
            yield mb.get_message_data()
            cb = mb.create_content_builder(content_type="text")
            yield cb.set_text(
                f"[ERROR] {chunk.get('error')} (code={chunk.get('code')})",
            )
            yield cb.complete()
            yield mb.complete()
            return

        items = _extract_alias_messages(chunk)
        if not items:
            continue

        for item in items:
            (
                alias_item_id,
                alias_type,
                alias_status,
                inner,
            ) = _extract_item_fields(item)

            if alias_type == "tool_use":
                call_id, tool_name, args = _parse_tool_use(
                    inner,
                    alias_item_id,
                )

                if alias_status != "finished":
                    continue

                if call_id in seen_tool_use:
                    continue
                seen_tool_use.add(call_id)

                fc = FunctionCall(
                    call_id=call_id,
                    name=tool_name,
                    arguments=_json_dumps_always(args),
                )
                data = DataContent(data=fc.model_dump())
                msg = Message(
                    type=MessageType.PLUGIN_CALL,
                    role="assistant",
                    content=[data],
                )
                yield msg.completed()
                continue

            if alias_type == "tool_result":
                call_id, tool_name, output_obj = _parse_tool_result(
                    inner,
                    alias_item_id,
                )

                if call_id in seen_tool_result:
                    continue
                if alias_status == "finished":
                    seen_tool_result.add(call_id)
                else:
                    continue

                fco = FunctionCallOutput(
                    call_id=call_id,
                    name=tool_name,
                    output=_json_dumps_always(output_obj),
                )
                data = DataContent(data=fco.model_dump())
                msg = Message(
                    type=MessageType.PLUGIN_CALL_OUTPUT,
                    role="tool",
                    content=[data],
                )
                yield msg.completed()

                if _is_plan_confirmation_prompt(output_obj):
                    prompt_text = _extract_prompt_text(output_obj)

                    mb2 = rb.create_message_builder(
                        message_type=MessageType.MESSAGE,
                        role="assistant",
                    )
                    yield mb2.get_message_data()
                    cb2 = mb2.create_content_builder(content_type="text")
                    yield cb2.set_text(prompt_text)
                    yield cb2.complete()
                    yield mb2.complete()

                continue

            k = _text_key(chunk, alias_item_id, alias_type)
            if k not in text_states:
                mb = rb.create_message_builder(
                    message_type=MessageType.MESSAGE,
                    role="assistant",
                )
                msg_obj = mb.get_message_data()
                msg_obj.metadata = {
                    "alias_task_id": chunk.get("task_id"),
                    "alias_conversation_id": chunk.get("conversation_id"),
                    "alias_user_id": chunk.get("user_id"),
                    "alias_chunk_message_id": chunk.get("message_id"),
                    "alias_item_id": item.get("id"),
                    "alias_parent_message_id": item.get("parent_message_id"),
                    "alias_inner": inner,
                }
                yield msg_obj
                cb = mb.create_content_builder(content_type="text")
                text_states[k] = _TextMsgState(mb=mb, cb=cb, last_text="")

            st = text_states[k]
            curr = str(inner.get("content") or "")
            delta = _compute_delta(st.last_text, curr)
            st.last_text = curr
            if delta:
                yield st.cb.add_text_delta(delta)

            if alias_status == "finished":
                yield st.cb.complete()
                yield st.mb.complete()
                text_states.pop(k, None)

    for st in list(text_states.values()):
        try:
            yield st.cb.complete()
        except Exception:
            pass
        try:
            yield st.mb.complete()
        except Exception:
            pass
