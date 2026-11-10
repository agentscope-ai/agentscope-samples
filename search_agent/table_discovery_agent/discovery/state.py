# -*- coding: utf-8 -*-
"""Track branches of the table discovery workflow."""

import json
from collections.abc import Iterator
from copy import deepcopy
from typing import Any, TypedDict

from agentscope.module import StateModule

from table_tools.combiner import Match

from .constraints import QueryConstraint


class _Node(TypedDict):
    """A tool call and its outcome, or the root seed."""

    id: str
    parent_id: str | None
    tool_name: str | None
    inputs: dict[str, Any]
    matches: list[Match]
    constraints: list[QueryConstraint]
    ended: bool
    terminated: bool
    error: str | None


def _restore_nodes(nodes: dict[str, _Node]) -> dict[str, _Node]:
    """Copy the serialized nodes and supply constraints for older snapshots."""
    restored = deepcopy(nodes)
    for node in restored.values():
        node.setdefault("constraints", [])
    return restored


class DiscoveryState(StateModule):
    """Store tool attempts and their candidate matches in a rooted tree."""

    def __init__(
        self,
        seed_matches: list[Match] | None = None,
        *,
        initial_constraints: list[QueryConstraint] | None = None,
    ) -> None:
        super().__init__()
        self._nodes: dict[str, _Node] = {
            "0": {
                "id": "0",
                "parent_id": None,
                "tool_name": None,
                "inputs": {},
                "matches": deepcopy(seed_matches or []),
                "constraints": deepcopy(initial_constraints or []),
                "ended": False,
                "terminated": False,
                "error": None,
            },
        }
        self._next_id = 1
        self.register_state(
            "_nodes",
            custom_to_json=deepcopy,
            custom_from_json=_restore_nodes,
        )
        self.register_state("_next_id")

    def get_node(self, node_id: str) -> _Node:
        """Return a copy of the requested node."""
        return deepcopy(self._nodes[node_id])

    def trajectory_ids(self, node_id: str) -> list[str]:
        """Return node IDs from the selected node to the root."""
        trajectory = []
        current_id: str | None = node_id
        while current_id is not None:
            trajectory.append(current_id)
            current_id = self._nodes[current_id]["parent_id"]
        return trajectory

    def iter_nodes(self) -> Iterator[_Node]:
        """Yield snapshots of the nodes in insertion order."""
        for node in self._nodes.values():
            yield deepcopy(node)

    def iter_active_leaves(self) -> Iterator[tuple[str, int, int]]:
        """Yield each active leaf's node ID, depth, and pending count."""
        parents = {node["parent_id"] for node in self._nodes.values()}
        depths: dict[str, int] = {}
        for node_id, node in self._nodes.items():
            parent = node["parent_id"]
            depth = 0 if parent is None else depths[parent] + 1
            depths[node_id] = depth
            if node_id not in parents and not node["ended"]:
                yield node_id, depth, len(node["constraints"])

    def min_pending_constraints(self) -> int:
        """Return the smallest pending count across non-error nodes."""
        return min(
            len(node["constraints"])
            for node in self._nodes.values()
            if node["error"] is None
        )

    def get_matches(self, node_id: str) -> list[Match]:
        """Return a copy of the matches at the requested node."""
        return deepcopy(self._nodes[node_id]["matches"])

    def get_initial_constraints(self) -> list[QueryConstraint]:
        """Return a copy of the constraints supplied at the start."""
        return deepcopy(self._nodes["0"]["constraints"])

    def add_child(
        self,
        parent_id: str,
        tool_name: str,
        inputs: dict[str, Any],
        matches: list[Match],
        *,
        constraints: list[QueryConstraint] | None = None,
        terminated: bool = False,
        error: str | None = None,
    ) -> str:
        """Record a tool attempt and return its new node ID."""
        if parent_id not in self._nodes:
            raise KeyError(parent_id)
        if constraints is None:
            constraints = self._nodes[parent_id]["constraints"]

        node_id = str(self._next_id)
        self._nodes[node_id] = {
            "id": node_id,
            "parent_id": parent_id,
            "tool_name": tool_name,
            "inputs": deepcopy(inputs),
            "matches": deepcopy(matches),
            "constraints": deepcopy(constraints),
            "ended": terminated or error is not None or not matches,
            "terminated": terminated,
            "error": error,
        }
        self._next_id += 1
        return node_id

    def already_tried(self, tool_name: str, inputs: dict[str, Any]) -> bool:
        """Check for an equivalent tool call that completed without error."""
        canonical_inputs = json.dumps(inputs, sort_keys=True)
        return any(
            node["error"] is None
            and node["tool_name"] == tool_name
            and json.dumps(node["inputs"], sort_keys=True) == canonical_inputs
            for node in self._nodes.values()
        )

    def collect_candidates(self) -> list[Match]:
        """Normalize and merge the last available results from each branch."""
        parents = {node["parent_id"] for node in self._nodes.values()}
        frontiers: set[str] = set()
        candidates: dict[str, Match] = {}

        for node in self._nodes.values():
            if node["id"] in parents or node["error"] is not None:
                continue

            frontier = node
            while not frontier["matches"]:
                parent_id = frontier["parent_id"]
                if parent_id is None:
                    break
                frontier = self._nodes[parent_id]
            if (
                frontier["id"] == "0"
                or frontier["error"] is not None
                or frontier["id"] in frontiers
            ):
                continue
            frontiers.add(frontier["id"])

            matches = frontier["matches"]
            scale = max(match["score"] for match in matches) or 1.0
            for match in matches:
                table_id = match["table_id"]
                score = match["score"] / scale
                if table_id not in candidates:
                    candidates[table_id] = deepcopy(match)
                    candidates[table_id]["score"] = score
                else:
                    first = candidates[table_id]
                    first["score"] = max(first["score"], score)

        return list(candidates.values())
