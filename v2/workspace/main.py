# -*- coding: utf-8 -*-
"""
AgentScope 2.0 Workspace - Backend Switching Example

This example demonstrates how to create an Agent backed by a workspace,
and how to switch between the supported workspace backends:

* ``local``      - LocalWorkspace: a plain directory on the host filesystem.
* ``docker``     - DockerWorkspace: an isolated Docker container.
* ``opensandbox`` - OpenSandboxWorkspace: a remote OpenSandbox sandbox.

Only the ``local`` backend needs no external dependency and runs out of the
box. The ``docker`` and ``opensandbox`` backends require Docker or an
OpenSandbox account respectively, and are shown for completeness.

Usage:
    python main.py --backend local
    python main.py --backend docker
    python main.py --backend opensandbox
"""
import argparse
import asyncio
import os

from agentscope.agent import Agent
from agentscope.tool import Toolkit
from agentscope.workspace import (
    DockerWorkspace,
    LocalWorkspace,
    OpenSandboxWorkspace,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a workspace-backed agent with a selectable backend.",
    )
    parser.add_argument(
        "--backend",
        choices=["local", "docker", "opensandbox"],
        default="local",
        help="The workspace backend to use (default: local).",
    )
    parser.add_argument(
        "--workdir",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "workspace",
        ),
        help="The workspace root directory (local backend).",
    )
    args = parser.parse_args()

    # Select the workspace backend. All backends expose the same interface
    # (list_tools / list_skills / get_instructions / get_backend), so the
    # rest of the example is backend-agnostic.
    if args.backend == "local":
        workspace = LocalWorkspace(workdir=args.workdir)
    elif args.backend == "docker":
        # Requires a local Docker daemon. The image is built on first use.
        workspace = DockerWorkspace(host_workdir=args.workdir)
    else:
        # Requires an OpenSandbox account. The API key is read from the
        # environment by the SDK when ``api_key`` is left empty.
        workspace = OpenSandboxWorkspace()

    # The workspace is an async context manager: it initializes the backend
    # on enter and tears it down on exit.
    async with workspace:
        print(f"Using workspace backend: {args.backend}")

        # Filesystem tools and skills are provided by the workspace, bound
        # to its backend.
        tools = await workspace.list_tools()
        print(f"Loaded {len(tools)} filesystem tool(s).")

        instructions = await workspace.get_instructions()
        print("Workspace instructions loaded.")

        # A real agent would plug in a model here. For a dependency-free
        # demo we only show how the workspace wiring is assembled.
        toolkit = Toolkit(tools=tools)
        schemas = await toolkit.get_tool_schemas()
        print(f"Agent toolkit ready: {len(schemas)} tool schema(s) exposed.")

        # Uncomment to run a model-backed agent once you have configured a
        # model credential:
        # agent = Agent(
        #     name="Friday",
        #     system_prompt=instructions,
        #     model=...,
        #     toolkit=toolkit,
        # )
        # await agent.reply("List the files in the workspace.")


if __name__ == "__main__":
    asyncio.run(main())
