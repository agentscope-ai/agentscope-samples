# -*- coding: utf-8 -*-
"""
Create a qa agent with name, system_prompt, tools, model, file and
collection_name.

Example:
  python -m alias.agent.agents.create_agent -n QA -a qaagent
  --task "What's agentscope?"
"""
import argparse
import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import List, Optional, Union

from agentscope.message import Msg
from alias.agent.agents import AliasAgentBase, QAAgent
from alias.agent.tools import AliasToolkit
from alias.agent.tools.add_tools import add_tools
from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox


def _ensure_env():
    """Optional .env for DASHSCOPE_API_KEY. Returns (path or None, created)."""
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
            p.write_text(
                "ENVIRONMENT=local\nDASHSCOPE_API_KEY=your_key_here\n",
            )
            return p, True
        except Exception:
            pass
    return None, False


def normalize_agent_type(agent: str) -> str:
    """Normalize agent type: qaagent/QAAgent/QA_Agent
    -> 'qaagent'; else 'alias'."""
    if not agent or not agent.strip():
        return "alias"
    t = agent.strip().lower().replace("_", "").replace("-", "")
    return "qaagent" if t == "qaagent" else "alias"


def resolve_system_prompt(system_prompt: Optional[str]) -> str:
    """Path -> file content; else as-is. None/empty -> ''."""
    if not system_prompt or not system_prompt.strip():
        return system_prompt or ""
    p = Path(system_prompt.strip())
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return system_prompt


def normalize_tools(tools: Union[None, str, List[str]]) -> List[str]:
    """Normalize tools to list of names.
    str -> [str], list -> list, None -> []."""
    if tools is None:
        return []
    if isinstance(tools, str):
        return (
            [t.strip() for t in tools.split(",") if t.strip()]
            if tools.strip()
            else []
        )
    if isinstance(tools, list):
        return [t if isinstance(t, str) else str(t) for t in tools]
    return []


async def ainput(prompt: str) -> str:
    """Async input so event loop is not blocked."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


def normalize_file_list(file: Union[None, str, List[str]]) -> List[str]:
    """Normalize file to list of paths. None/str/list -> list of paths."""
    if file is None:
        return []
    if isinstance(file, str):
        return [p.strip() for p in file.split(",") if p.strip()]
    return [str(p) for p in file]


async def run_agent_with_chat(  # pylint: disable=too-many-branches
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
    Create agent (AliasAgentBase or QAAgent). If agent_type is 'qaagent',
    create QAAgent with file/collection_name; else AliasAgentBase.
    file: for QAAgent only (list of paths or comma-separated str).
    task: if set, sent as first user message.
    """
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("DASHSCOPE_API_KEY not set, skip.")
        return

    prompt_text = resolve_system_prompt(system_prompt)
    tools_list = normalize_tools(tools)
    agent_type = normalize_agent_type(agent_type)
    file_list = normalize_file_list(file) if file is not None else None

    sandbox = None
    worker_full_toolkit = None
    try:
        sandbox = AliasSandbox()
        sandbox.__enter__()
    except Exception as e:
        print(f"Sandbox start failed: {e}")
        print(
            "Hint: docker run -d -p 6379:6379 "
            "--name alias-redis redis:7-alpine",
        )
        return

    try:
        worker_full_toolkit = AliasToolkit(sandbox, add_all=True)
        await add_tools(worker_full_toolkit)

        if agent_type == "qaagent":
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

        if task and task.strip():
            await agent(
                Msg(name="user", content=task.strip(), role="user"),
            )

        while True:
            user_input = await ainput(
                "User (Enter `exit` or `quit` to exit): ",
            )
            if not user_input or user_input.strip().lower() in (
                "exit",
                "quit",
            ):
                print("Exiting.")
                break
            await agent(
                Msg(name="user", content=user_input.strip(), role="user"),
            )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted.")
    except Exception as e:
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
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        required=True,
        help="Agent name",
    )
    parser.add_argument(
        "--system_prompt",
        "-s",
        type=str,
        default=None,
        help="System prompt or path to file. None = agent default.",
    )
    parser.add_argument(
        "--tools",
        "-t",
        type=str,
        default="",
        help="Tool names, comma-separated or one. Empty = no extra tools.",
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
        help="Initial question/task; if set, sent as first message.",
    )
    parser.add_argument(
        "--agent",
        "-a",
        type=str,
        default="alias",
        help="Agent type: 'qaagent' for QAAgent; else AliasAgentBase.",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        nargs="*",
        help="For QAAgent: RAG file path(s). Space- or comma-separated.",
    )
    parser.add_argument(
        "--collection_name",
        type=str,
        default=None,
        help="For QAAgent: Qdrant collection name (default as_faq).",
    )
    args = parser.parse_args()

    # Normalize --file: nargs='*' gives list or single element
    file_arg = args.file
    if (
        file_arg is not None
        and isinstance(file_arg, list)
        and len(file_arg) == 0
    ):
        file_arg = None
    if (
        file_arg is not None
        and isinstance(file_arg, list)
        and len(file_arg) == 1
    ):
        file_arg = file_arg[0] if file_arg[0] else None
    if file_arg is not None and isinstance(file_arg, list):
        file_arg = [p for p in file_arg if p]

    if not sys.stdout.isatty():
        sys.stdout.reconfigure(line_buffering=True)

    _env_file, _created_env = _ensure_env()
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
                collection_name=(
                    args.collection_name.strip()
                    if args.collection_name
                    else None
                ),
            ),
        )
    finally:
        if _created_env and _env_file and _env_file.exists():
            _env_file.unlink()


if __name__ == "__main__":
    main()
