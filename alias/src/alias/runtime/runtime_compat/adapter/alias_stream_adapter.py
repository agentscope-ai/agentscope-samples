# -*- coding: utf-8 -*-
import json
from typing import Any, AsyncIterator, Dict, Optional, Union

from agentscope_runtime.engine.helpers.agent_api_builder import ResponseBuilder
from agentscope_runtime.engine.schemas.agent_schemas import (
    Content,
    ContentType,
    FunctionCall,
    FunctionCallOutput,
    Message,
    MessageType,
    Role,
)


def _try_deep_parse(val: Any) -> Any:
    """
    Recursively parse JSON-like strings into native Python objects.
    """
    if isinstance(val, str):
        content = val.strip()
        if (content.startswith("{") and content.endswith("}")) or (
            content.startswith("[") and content.endswith("]")
        ):
            try:
                parsed = json.loads(content)
                return _try_deep_parse(parsed)
            except Exception:
                # If nested JSON parsing fails, treat it as a normal string.
                return val
        return val
    if isinstance(val, list):
        return [_try_deep_parse(i) for i in val]
    if isinstance(val, dict):
        return {k: _try_deep_parse(v) for k, v in val.items()}
    return val


def _ensure_safe_json_string(val: Any) -> str:
    """
    Serialize content into a valid JSON string suitable for WebUI parsing.
    """
    parsed_val = _try_deep_parse(val)
    if parsed_val is None:
        return "{}"
    return json.dumps(parsed_val, ensure_ascii=False)


def _extract_alias_output_obj(content_str: str) -> Any:
    """
    Extract the `output` object from Alias nested tool-result content.
    """
    try:
        data = json.loads(content_str)
        if isinstance(data, list) and data:
            return data[0].get("output")
    except Exception:
        # Best-effort parse: if the string is not a valid
        # JSON or doesn't follow the expected structure,
        # fall back to returning the original string.
        pass
    return content_str


class AliasAdapterState:
    def __init__(
        self,
        message_builder: Any,
        content_builder: Any,
        runtime_type: str,
    ):
        self.mb = message_builder
        self.cb = content_builder
        self.runtime_type = runtime_type
        self.last_content = ""
        self.is_completed = False


async def adapt_alias_message_stream(
    source_stream: AsyncIterator[Dict[str, Any]],
) -> AsyncIterator[Union[Message, Content]]:
    # pylint: disable=too-many-branches, too-many-statements
    rb = ResponseBuilder()
    state_map: Dict[str, AliasAdapterState] = {}
    last_active_key: Optional[str] = None

    yield rb.created()
    yield rb.in_progress()

    async for chunk in source_stream:
        if not isinstance(chunk, dict) or "data" not in chunk:
            continue

        messages = chunk["data"].get("messages") or []
        for item in messages:
            alias_id = item.get("id")
            inner_msg = item.get("message") or {}

            alias_type = inner_msg.get("type")
            alias_status = inner_msg.get("status")
            tool_call_id = inner_msg.get("tool_call_id") or alias_id

            if alias_type in ["thought", "sub_thought"]:
                runtime_type = MessageType.REASONING
                target_role = Role.ASSISTANT
            elif alias_type in ["tool_call", "tool_use"]:
                runtime_type = MessageType.PLUGIN_CALL
                target_role = Role.ASSISTANT
            elif alias_type == "tool_result":
                runtime_type = MessageType.PLUGIN_CALL_OUTPUT
                target_role = Role.TOOL
            else:
                runtime_type = MessageType.MESSAGE
                target_role = Role.ASSISTANT

            state_key = f"{tool_call_id}_{runtime_type}"

            if last_active_key and last_active_key != state_key:
                old_state = state_map.get(last_active_key)
                if old_state and not old_state.is_completed:
                    yield old_state.cb.complete()
                    yield old_state.mb.complete()
                    old_state.is_completed = True

            last_active_key = state_key

            if state_key not in state_map:
                mb = rb.create_message_builder(role=target_role)
                mb.message.type = runtime_type
                yield mb.get_message_data()

                if runtime_type in [
                    MessageType.PLUGIN_CALL,
                    MessageType.PLUGIN_CALL_OUTPUT,
                ]:
                    c_type = ContentType.DATA
                else:
                    c_type = ContentType.TEXT

                cb = mb.create_content_builder(content_type=c_type)
                state_map[state_key] = AliasAdapterState(mb, cb, runtime_type)

            state = state_map[state_key]

            if runtime_type in [MessageType.MESSAGE, MessageType.REASONING]:
                raw_text = str(inner_msg.get("content") or "")

                if alias_type == "files" and "files" in inner_msg:
                    raw_text = "\n".join(
                        [
                            f"📁 [{f['filename']}]({f['url']})"
                            for f in inner_msg["files"]
                        ],
                    )

                if raw_text.startswith(state.last_content):
                    delta = raw_text[len(state.last_content) :]
                    if delta:
                        yield state.cb.add_text_delta(delta)
                    state.last_content = raw_text
                else:
                    yield state.cb.set_text(raw_text)
                    state.last_content = raw_text

            elif runtime_type == MessageType.PLUGIN_CALL:
                args = inner_msg.get("arguments") or {}
                fc = FunctionCall(
                    call_id=tool_call_id,
                    name=inner_msg.get("tool_name") or "tool",
                    arguments=_ensure_safe_json_string(args),
                )
                yield state.cb.set_data(fc.model_dump())

            elif runtime_type == MessageType.PLUGIN_CALL_OUTPUT:
                output_obj = _extract_alias_output_obj(
                    inner_msg.get("content", ""),
                )
                fco = FunctionCallOutput(
                    call_id=tool_call_id,
                    name=inner_msg.get("tool_name") or "tool",
                    output=_ensure_safe_json_string(output_obj),
                )
                yield state.cb.set_data(fco.model_dump())

            if alias_status == "finished" and not state.is_completed:
                yield state.cb.complete()
                yield state.mb.complete()
                state.is_completed = True

    for state in state_map.values():
        if not state.is_completed:
            try:
                yield state.cb.complete()
                yield state.mb.complete()
                state.is_completed = True
            except Exception:
                # Graceful cleanup: ignore errors during the
                # finalization phase to ensure the main response
                # stream can finish without crashing.
                pass

    yield rb.completed()
