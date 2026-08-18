# -*- coding: utf-8 -*-
"""Offline tests for the Xquik MCP discovery sample."""

import json
import os
import sys
import unittest
from unittest.mock import patch

from .main import (
    DEFAULT_MCP_URL,
    DEFAULT_QUERY,
    _explore_code,
    _extract_text,
    _mcp_client,
    _query_from_args,
    _required_api_key,
)


class XquikMCPDiscoveryTest(unittest.TestCase):
    def test_required_api_key_is_trimmed(self) -> None:
        with patch.dict(
            os.environ,
            {"XQUIK_API_KEY": "  test-key  "},
            clear=False,
        ):
            self.assertEqual(_required_api_key(), "test-key")

    def test_required_api_key_rejects_empty_value(self) -> None:
        with patch.dict(os.environ, {"XQUIK_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(SystemExit, "Set XQUIK_API_KEY"):
                _required_api_key()

    def test_query_uses_arguments_or_default(self) -> None:
        with patch.object(sys, "argv", ["main.py", "Twitter", "Trends"]):
            self.assertEqual(_query_from_args(), "twitter trends")
        with patch.object(sys, "argv", ["main.py"]):
            self.assertEqual(_query_from_args(), DEFAULT_QUERY)

    def test_explore_code_escapes_query_and_bounds_results(self) -> None:
        query = 'trends"); throw new Error("unexpected")'
        code = _explore_code(query)
        self.assertIn(json.dumps(query), code)
        self.assertIn(".slice(0, 10)", code)

    def test_client_uses_fixed_origin_and_read_only_tool(self) -> None:
        client = _mcp_client("test-key")
        self.assertEqual(client.mcp_config.url, DEFAULT_MCP_URL)
        self.assertEqual(
            client.mcp_config.headers,
            {"Authorization": "Bearer test-key"},
        )
        self.assertEqual(client.enable_tools, ["explore"])
        self.assertFalse(client.is_stateful)

    def test_extract_text_joins_text_and_fallback_content(self) -> None:
        text_item = type("TextItem", (), {"text": "first"})()
        fallback = type("Fallback", (), {"text": None})()
        result = type("Result", (), {"content": [text_item, fallback]})()
        self.assertEqual(
            _extract_text(result),
            f"first\n{fallback}",
        )


if __name__ == "__main__":
    unittest.main()
