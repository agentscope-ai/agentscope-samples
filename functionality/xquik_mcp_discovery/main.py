# -*- coding: utf-8 -*-
"""Read-only AgentScope MCP discovery sample for Xquik."""

import asyncio
import json
import os
import sys
from typing import Any

from agentscope.mcp import HttpMCPConfig, MCPClient


DEFAULT_MCP_URL = "https://xquik.com/mcp"
DEFAULT_QUERY = "radar"


def _required_api_key() -> str:
    api_key = os.environ.get("XQUIK_API_KEY", "").strip()
    if api_key == "":
        raise SystemExit("Set XQUIK_API_KEY before running this sample.")
    return api_key


def _query_from_args() -> str:
    query = " ".join(sys.argv[1:]).strip().lower()
    return query if query else DEFAULT_QUERY


def _extract_text(result: Any) -> str:
    content = getattr(result, "content", [])
    parts = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


def _explore_code(query: str) -> str:
    query_literal = json.dumps(query)
    return f"""
async () => spec.endpoints
  .filter((endpoint) => {{
    const haystack = `${{endpoint.method}} ${{endpoint.path}} ${{endpoint.category}} ${{endpoint.summary}}`.toLowerCase();
    return haystack.includes({query_literal});
  }})
  .slice(0, 10)
  .map((endpoint) => ({{
    method: endpoint.method,
    path: endpoint.path,
    category: endpoint.category,
    summary: endpoint.summary,
    free: endpoint.free
  }}))
"""


async def main() -> None:
    client = MCPClient(
        name="xquik",
        is_stateful=False,
        enable_tools=["explore"],
        mcp_config=HttpMCPConfig(
            type="http_mcp",
            url=os.environ.get("XQUIK_MCP_URL", DEFAULT_MCP_URL),
            headers={"Authorization": f"Bearer {_required_api_key()}"},
        ),
    )

    explore = await client.get_tool("explore")
    result = await explore(code=_explore_code(_query_from_args()))
    print(_extract_text(result))


if __name__ == "__main__":
    asyncio.run(main())
