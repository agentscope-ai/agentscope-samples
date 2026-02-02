# -*- coding: utf-8 -*-
"""
Create a qa agent with name, system_prompt, tools, model, file and collection_name.

Example:
python -m alias.agent.agents.create_agent -n QA -a qaagent --task "What's agentscope?"
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional, Union

# Optional .env for DASHSCOPE_API_KEY
def _ensure_env():
    cwd = Path(os.getcwd()).resolve()
    for _ in range(4):
        p = cwd / ".env"
        if p.exists():
            return None, False
        if cwd.parent == cwd:
            break
        cwd = cwd.parent
    p = Path(os.getcwd()) / ".env"
    if not p.exists():
        try:
            p.write_text("ENVIRONMENT=local\nDASHSCOPE_API_KEY=test_key\n")
            return p, True
        except Exception:
            pass
    return None, False

_env_file, _created_env = _ensure_env()

from agentscope.message import Msg
from alias.agent.agents import AliasAgentBase, QAAgent
from alias.agent.tools import AliasToolkit
from alias.agent.tools.add_tools import add_tools
from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox


def normalize_agent_type(agent: str) -> str:
    """Normalize agent type: qaagent, QAAgent, QA_Agent, qa_agent -> 'qaagent'; else 'alias'."""
    if not agent or not agent.strip():
        return "alias"
    t = agent.strip().lower().replace("_", "").replace("-", "")
    return "qaagent" if t == "qaagent" else "alias"


def resolve_system_prompt(system_prompt: Optional[str]) -> str:
    """If system_prompt is a path to an existing file, return its content; else return as-is. None/empty -> ''."""
    if not system_prompt or not system_prompt.strip():
        return system_prompt or ""
    p = Path(system_prompt.strip())
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return system_prompt


def normalize_tools(tools: Union[None, str, List[str]]) -> List[str]:
    """Normalize tools to a list of tool names. str -> [str], list -> list, None/empty -> []."""
    if tools is None:
        return []
    if isinstance(tools, str):
        return [t.strip() for t in tools.split(",") if t.strip()] if tools.strip() else []
    if isinstance(tools, list):
        return [t if isinstance(t, str) else str(t) for t in tools]
    return []


async def ainput(prompt: str) -> str:
    """Async input so event loop is not blocked."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


def normalize_file_list(file: Union[None, str, List[str]]) -> List[str]:
    """Normalize file to list of paths. file can be None, a str (single path or comma-separated), or a list of paths."""
    if file is None:
        return []
    if isinstance(file, str):
        return [p.strip() for p in file.split(",") if p.strip()]
    return [str(p) for p in file]


async def run_agent_with_chat(
    name: str,
    system_prompt: Optional[str] = None,
    tools: Union[None, str, List[str]] = None,
    model: str = "qwen3-max",
    task: Union[None, str] = None,
    agent_type: str = "alias",
    file: Union[None, str, List[str]] = None,
    collection_name: Union[None, str] = None,
) -> None:
    """
    Create agent (AliasAgentBase or QAAgent)
    If agent_type is 'qaagent', create QAAgent with file/collection_name; else create AliasAgentBase.
    file: for QAAgent only; can be a list of paths or a single str (one path or comma-separated paths).
    If task is provided, send it as the first user message before the input loop.
    """
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("DASHSCOPE_API_KEY not set, skip.")
        return

    prompt_text = resolve_system_prompt(system_prompt)
    tools_list = normalize_tools(tools)
    agent_kind = normalize_agent_type(agent_type)
    file_list = normalize_file_list(file) if file is not None else None

    sandbox = None
    worker_full_toolkit = None
    try:
        sandbox = AliasSandbox()
        sandbox.__enter__()
    except Exception as e:
        print(f"Sandbox start failed: {e}")
        print("Hint: docker run -d -p 6379:6379 --name alias-redis redis:7-alpine")
        return

    try:
        worker_full_toolkit = AliasToolkit(sandbox, add_all=True)
        await add_tools(worker_full_toolkit)

        if agent_kind == "qaagent":
            agent = await QAAgent.create(
                name=name,
                model=model,
                system_prompt=prompt_text or None,
                tools=tools_list if tools_list else None,
                worker_full_toolkit=worker_full_toolkit,
                use_long_term_memory_service=False,
                file=file_list,
                collection_name=collection_name,
            )
        else:
            agent = await AliasAgentBase.create(
                name=name,
                model=model,
                system_prompt=prompt_text or None,
                tools=tools_list if tools_list else None,
                worker_full_toolkit=worker_full_toolkit,
                use_long_term_memory_service=False,
            )

        # Optional initial task: send as first user message
        if task and task.strip():
            response = await agent(Msg(name="user", content=task.strip(), role="user"))
            content = getattr(response, "content", None) or str(response)

        while True:
            user_input = await ainput("User (Enter `exit` or `quit` to exit): ")
            if not user_input or user_input.strip().lower() in ("exit", "quit"):
                print("Exiting.")
                break
            response = await agent(Msg(name="user", content=user_input.strip(), role="user"))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted.")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        if worker_full_toolkit is not None:
            try:
                await worker_full_toolkit.close_mcp_clients()
            except Exception:
                pass
        if sandbox is not None:
            try:
                sandbox.__exit__(None, None, None)
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--name", "-n", type=str, required=True, help="Agent name")
    parser.add_argument(
        "--system_prompt",
        "-s",
        type=str,
        default=None,
        help="System prompt string or path to a file. If None, agent uses its default prompt.",
    )
    parser.add_argument(
        "--tools",
        "-t",
        type=str,
        default="",
        help="Comma-separated tool names, or single name (e.g. tavily_search or tavily_search,read_file). Empty for no extra tools.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="qwen3-max",
        help="Model name (default: qwen3-max)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default="",
        help="Initial user question/task; if set, sent as first message before multi-turn input.",
    )
    parser.add_argument(
        "--agent",
        "-a",
        type=str,
        default="alias",
        help="Agent type: 'qaagent' (or QAAgent/QA_Agent/qa_agent) for QAAgent; else AliasAgentBase (default).",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        nargs="*",
        help="For QAAgent: file path(s) for RAG. Can be list (space-separated) or single str (comma-separated). Ignored for AliasAgentBase.",
    )
    parser.add_argument(
        "--collection_name",
        type=str,
        default=None,
        help="For QAAgent: Qdrant collection name for RAG (default as_faq). Ignored for AliasAgentBase.",
    )
    args = parser.parse_args()

    # Normalize --file: nargs='*' gives list or single element
    file_arg = args.file
    if file_arg is not None and isinstance(file_arg, list) and len(file_arg) == 0:
        file_arg = None
    if file_arg is not None and isinstance(file_arg, list) and len(file_arg) == 1:
        file_arg = file_arg[0] if file_arg[0] else None
    if file_arg is not None and isinstance(file_arg, list):
        file_arg = [p for p in file_arg if p]

    if not sys.stdout.isatty():
        sys.stdout.reconfigure(line_buffering=True)

    try:
        asyncio.run(
            run_agent_with_chat(
                name=args.name,
                system_prompt=args.system_prompt,
                tools=args.tools.strip() or None,
                model=args.model,
                task=args.task.strip() or None,
                agent_type=args.agent,
                file=file_arg,
                collection_name=args.collection_name.strip() if args.collection_name else None,
            ),
        )
    finally:
        if _created_env and _env_file and _env_file.exists():
            _env_file.unlink()


if __name__ == "__main__":
    main()
