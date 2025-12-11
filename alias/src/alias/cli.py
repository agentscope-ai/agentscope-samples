#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=R0912
"""
Alias Command Line Interface

This module provides a terminal executable entry point
for the Alias agent application.
"""
import argparse
import asyncio
import os
import signal
import sys
import traceback
import webbrowser
from typing import Optional

from loguru import logger

from agentscope.agent import TerminalUserInput, UserAgent

from alias.agent.mock import MockSessionService, UserMessage
from alias.agent.run import (
    arun_meta_planner,
    arun_browseruse_agent,
    arun_deepresearch_agent,
    arun_datascience_agent,
    arun_finance_agent,
)
from alias.agent.tools.sandbox_util import copy_local_file_to_workspace
from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox


# Global variable to store the original signal handler
_original_sigint_handler = None


def _safe_sigint_handler(signum, frame):  # pylint: disable=W0613
    """Signal handler that cancels tasks instead of raising SystemExit."""
    logger.info(
        "Custom SIGINT handler triggered - preventing sandbox shutdown",
    )
    # Get the current event loop if running
    try:
        loop = asyncio.get_running_loop()
        if loop and loop.is_running():
            # Cancel all running tasks to propagate CancelledError
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            logger.info(f"Cancelling {len(tasks)} tasks due to SIGINT")
            for task in tasks:
                task.cancel()
            logger.debug(f"Cancelled {len(tasks)} tasks due to SIGINT")
    except RuntimeError:
        # No running event loop, raise KeyboardInterrupt
        logger.info("No running event loop, raising KeyboardInterrupt")
        raise KeyboardInterrupt()  # pylint: disable=W0707


async def run_agent_task(
    user_msg: str,
    mode: str = "general",
    files: Optional[list[str]] = None,
    use_long_term_memory_service: bool = False,
) -> None:
    """
    Run an agent task with the specified configuration.

    Args:
        user_msg: The user's task/query
        mode: Agent mode ('general', 'dr', 'ds', 'browser', 'finance')
        files: List of local file paths to upload to sandbox workspace
        use_long_term_memory_service: Enable long-term memory service.
    """
    global _original_sigint_handler

    # Override signal handler BEFORE creating sandbox
    # This prevents the sandbox library's handler from destroying the container
    # if _original_sigint_handler is None:
    #     _original_sigint_handler = signal.signal(
    #         signal.SIGINT, _safe_sigint_handler
    #     )
    #     logger.debug("Installed custom SIGINT handler to protect sandbox")

    # Initialize session
    session = MockSessionService(
        use_long_term_memory_service=use_long_term_memory_service,
    )

    # Create initial user message
    user_agent = UserAgent(name="User")
    user_agent.override_instance_input_method(
        input_method=TerminalUserInput(
            input_hint="User (Enter `exit` or `quit` to exit): ",
        ),
    )

    # Run agent with sandbox context
    sandbox = AliasSandbox()
    sandbox.__enter__()

    # Re-install our signal handler AFTER sandbox creation
    # The sandbox library may have installed its own handler during __enter__
    # which would destroy the container. We need to override it again.
    if _original_sigint_handler is None:
        _original_sigint_handler = signal.signal(
            signal.SIGINT,
            _safe_sigint_handler,
        )
    else:
        # Re-install our handler even if we already saved the original
        # This ensures it takes precedence over the sandbox library's handler
        signal.signal(signal.SIGINT, _safe_sigint_handler)
    logger.debug("Re-installed custom SIGINT handler after sandbox creation")

    logger.info(
        f"Sandbox mount dir: {sandbox.get_info().get('mount_dir')}",
    )
    logger.info(f"Sandbox desktop URL: {sandbox.desktop_url}")
    webbrowser.open(sandbox.desktop_url)
    # Upload files to sandbox if provided
    if files:
        target_paths = []
        logger.info(
            f"Uploading {len(files)} file(s) to sandbox workspace...",
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
            logger.info(f"Successfully uploaded to {result}")

            target_paths.append(result.get("content", [])[0].get("text"))

        user_msg += "\n\nUser uploaded files:\n" + "\n".join(target_paths)

    # Create initial user message (regardless of whether files were uploaded)
    initial_user_message = UserMessage(
        content=user_msg,
    )
    await session.create_message(initial_user_message)

    try:
        await _run_agent_loop(
            mode=mode,
            session=session,
            user_agent=user_agent,
            sandbox=sandbox,
        )
    finally:
        # Ensure sandbox is properly cleaned up
        try:
            sandbox.__exit__(None, None, None)
        except Exception:
            pass
        # Restore original signal handler when done
        if _original_sigint_handler is not None:
            signal.signal(signal.SIGINT, _original_sigint_handler)
            _original_sigint_handler = None
            logger.debug("Restored original SIGINT handler")


async def _run_agent_loop(
    mode: str,
    session: MockSessionService,
    user_agent: UserAgent,
    sandbox: AliasSandbox,
) -> None:
    """
    Execute the agent loop with follow-up interactions.

    Args:
        mode: Agent mode to run
        session: Session service instance
        user_agent: User agent for interactive follow-ups
        sandbox: Sandbox accessible for all agents
        use_long_term_memory_service: Enable long-term memory service.
    """
    while True:
        # Run the appropriate agent based on mode
        try:
            if mode == "browser":
                await arun_browseruse_agent(
                    session,
                    sandbox=sandbox,
                )
            elif mode == "dr":
                await arun_deepresearch_agent(
                    session,
                    sandbox=sandbox,
                )
            elif mode == "ds":
                await arun_datascience_agent(
                    session,
                    sandbox=sandbox,
                )
            elif mode == "general":
                await arun_meta_planner(
                    session,
                    sandbox=sandbox,
                )
            elif mode == "finance":
                await arun_finance_agent(session, sandbox=sandbox)
            else:
                raise ValueError(f"Unknown mode: {mode}")

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Agent execution interrupted by user")
            # Continue to prompt for next action
        except RuntimeError as e:
            # Sandbox container may have been destroyed during interruption
            if "No container found" in str(e):  # pylint: disable=R1723
                logger.error(
                    "Sandbox container was destroyed during interruption. "
                    "Please restart the application to continue.",
                )
                logger.error(traceback.format_exc())
                break  # Exit the loop since sandbox is no longer available
            else:
                raise  # Re-raise other RuntimeErrors
        except Exception as e:
            logger.error(f"Error running {mode} mode: {e}")
            logger.error(traceback.format_exc())

        # Check for follow-up interaction
        follow_msg = await user_agent()
        if len(follow_msg.content) == 0 or follow_msg.content.lower() in [
            "exit",
            "quit",
        ]:
            logger.info("Exiting agent loop")
            break

        await session.create_message(UserMessage(content=follow_msg.content))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="alias",
        description="Alias Agent System",
        epilog=(
            "Example: alias run --mode general "
            "--task 'Analyze Meta stock performance'"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
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
        choices=["general", "dr", "ds", "browser", "finance"],
        default="general",
        help=(
            "Agent mode: "
            "'general' (meta planner with workers), "
            "'dr' (deep research agent), "
            "'ds' (data science agent), "
            "'browser' (browser agent)"
            "'finance' (finance agent)"
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

    run_parser.add_argument(
        "--use_long_term_memory",
        action="store_true",
        help="Enable long-term memory service for retrieving user profiling "
        "information at session start",
    )

    # Version command
    parser.add_argument(
        "--version",
        action="version",
        version="Alias 0.2.0",
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
                    use_long_term_memory_service=(
                        args.use_long_term_memory
                        if hasattr(args, "use_long_term_memory")
                        else False
                    ),
                ),
            )
        except (KeyboardInterrupt, SystemExit) as e:
            # Catch SystemExit from sandbox signal handler (if it still runs)
            # and KeyboardInterrupt for graceful handling
            if isinstance(e, SystemExit) and e.code == 0:
                # Convert SystemExit(0) to KeyboardInterrupt
                # for graceful handling
                logger.info("\nInterrupted by user (signal handler)")
                # Don't exit - let the exception propagate
                # naturally or be handled
                sys.exit(0)
            else:
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
