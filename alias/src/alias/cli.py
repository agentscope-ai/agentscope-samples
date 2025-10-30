#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alias Command Line Interface

This module provides a terminal executable entry point
for the Alias agent application.
"""
import json
from typing import Optional
import asyncio
import argparse
import sys
import os
import traceback
import webbrowser

from loguru import logger
from agentscope.agent import UserAgent, TerminalUserInput
from agentscope_runtime.sandbox import FilesystemSandbox, BrowserSandbox
from agentscope_runtime.sandbox.box.sandbox import Sandbox
from agentscope.mcp import StdIOStatefulClient

from alias.agent.mock import MockSessionService, UserMessage
from alias.agent.run import (
    arun_agents,
    test_browseruse_agent,
    test_deepresearch_agent,
)
from alias.agent.tools import AliasToolkit
from alias.agent.tools.improved_tools import DashScopeMultiModalTools
from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox
from alias.agent.tools.sandbox_util import copy_local_file_to_workspace


async def run_agent_task(
    user_msg: str,
    mode: str = "all",
    files: Optional[list[str]] = None,
) -> None:
    """
    Run an agent task with the specified configuration.
    
    Args:
        user_msg: The user's task/query
        mode: Agent mode ('all', 'worker', 'dr', 'browser')
        files: List of local file paths to upload to sandbox workspace
    """
    # Initialize session
    session = MockSessionService()

    # Create initial user message
    user_agent = UserAgent(name="User")
    user_agent.override_instance_input_method(
        input_method = TerminalUserInput(
            input_hint = "User (Enter `exit` or `quit` to exit): "
        )
    )
    
    # Run agent with sandbox context
    with AliasSandbox() as sandbox:
        logger.info(
            f"Sandbox mount dir: {sandbox.get_info().get('mount_dir')}"
        )
        logger.info(f"Sandbox desktop URL: {sandbox.desktop_url}")
        webbrowser.open(sandbox.desktop_url)
        # Upload files to sandbox if provided
        if files:
            target_paths = []
            logger.info(
                f"Uploading {len(files)} file(s) to sandbox workspace..."
            )
            for file_path in files:
                if not os.path.exists(file_path):
                    logger.error(f"File not found: {file_path}")
                    continue
                
                # Get the filename and construct target path in workspace
                filename = os.path.basename(file_path)
                target_path = f"/workspace/{filename}"
                
                logger.info(f"Uploading {file_path} to {target_path}")
                result = copy_local_file_to_workspace(
                    sandbox=sandbox,
                    local_path=file_path,
                    target_path=target_path,
                )
                
                if result.get("isError"):
                    raise ValueError(f"Failed to upload {file_path}: {result}")
                else:
                    logger.info(f"Successfully uploaded to {result}")

                target_paths.append(result.get("content", [])[0].get("text"))

            user_msg += "\n\nUser uploaded files:\n" + "\n".join(target_paths)

        initial_user_message = UserMessage(
            content=user_msg,
        )
        await session.create_message(initial_user_message)
        
        await _run_agent_loop(
            mode=mode,
            session=session,
            user_agent=user_agent,
            sandbox=sandbox
        )

async def _run_agent_loop(
    mode: str,
    session: MockSessionService,
    user_agent: UserAgent,
    sandbox: FilesystemSandbox,
) -> None:
    """
    Execute the agent loop with follow-up interactions.
    
    Args:
        mode: Agent mode to run
        session: Session service instance
        user_agent: User agent for interactive follow-ups
        sandbox: Sandbox accessible for all agents
    """
    while True:
        # Run the appropriate agent based on mode
        if mode == "browser":
            usr_msg = (await session.get_messages())[-1].message.get("content")
            logger.info(f"--> user_msg: {usr_msg}")
            await test_browseruse_agent(
                usr_msg,
                session,
                sandbox=sandbox,
            )
            break
        elif mode == "dr":
            usr_msg = (await session.get_messages())[-1].message.get("content")
            logger.info(f"--> user_msg: {usr_msg}")
            await test_deepresearch_agent(
                usr_msg,
                session,
                sandbox=sandbox,
            )
            break
        elif mode == "all":
            await arun_agents(
                session,
                sandbox=sandbox,
                enable_clarification=False,
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        # Check for follow-up interaction
        follow_msg = await user_agent()
        if (
            len(follow_msg.content) == 0
            or follow_msg.content.lower() in ["exit", "quit"]
        ):
            logger.info("Exiting agent loop")
            break
        
        await session.create_message(UserMessage(content=follow_msg.content))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="alias",
        description="Alias Agent System",
        epilog=(
            "Example: alias run --mode all "
            "--task 'Analyze Meta stock performance'"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run an agent task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    run_parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="The task or query for the agent to execute",
    )
    
    run_parser.add_argument(
        "--mode",
        choices=["all", "worker", "dr", "browser"],
        default="all",
        help=(
            "Agent mode: "
            "'all' (meta planner with workers), "
            "'worker' (single worker agent), "
            "'dr' (deep research agent), "
            "'browser' (browser agent)"
        ),
    )
    
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    run_parser.add_argument(
        "--files",
        "-f",
        type=str,
        nargs="+",
        help="Local file paths to upload to sandbox workspace "
             "for agent to use (e.g., --files file1.txt file2.csv)",
    )
    
    # Version command
    parser.add_argument(
        "--version",
        action="version",
        version="Alias 0.1.0",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if hasattr(args, "verbose") and args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Handle commands
    if args.command == "run":
        try:
            asyncio.run(
                run_agent_task(
                    user_msg=args.task,
                    mode=args.mode,
                    files=args.files if hasattr(args, "files") else None,
                )
            )
        except KeyboardInterrupt:
            logger.info("\nInterrupted by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            if hasattr(args, "verbose") and args.verbose:
                traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
