# -*- coding: utf-8 -*-
"""Run the table discovery tree through AgentScope."""

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import (
    AsyncIterable,
    Callable,
    Iterator,
    Mapping,
    Sequence,
)
from copy import deepcopy
from dataclasses import dataclass, replace
from functools import partial
from math import inf
from operator import itemgetter
from typing import Any, Literal, cast

from agentscope.agent import AgentBase
from agentscope.formatter import (
    DashScopeChatFormatter,
    DeepSeekChatFormatter,
    FormatterBase,
)
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg, TextBlock, ToolUseBlock
from agentscope.model import (
    ChatModelBase,
    ChatResponse,
    DashScopeChatModel,
    OpenAIChatModel,
)
from agentscope.tool import Toolkit, ToolResponse
from dashscope.common.error import DashScopeException
from openai import OpenAIError

from indexing import ColumnIndex, KeySketch, build_column_statistics
from indexing.column_matcher import ColumnNameMatcher
from indexing.embedding import ColumnEncoder
from discovery.constraints import (
    QueryConstraint,
    Scalar,
    extract_constraints,
    rank_results,
    resolve_constraints,
    satisfies,
)
from discovery.prompts import (
    OBSERVATION_RETRY_HINT,
    OBSERVATION_SYS_PROMPT,
    OBSERVATION_TEMPLATE,
    PLANNING_RETRY_HINT,
    PLANNING_SYS_PROMPT,
    PLANNING_TEMPLATE,
)
from discovery.relationship_graph import (
    RelationshipGraph,
    RelationshipPath,
    build_relationship_graph,
    find_paths,
)
from discovery.state import DiscoveryState, _Node
from table_tools.combiner import Match, combine_results
from table_tools.composite_seeker import TableOperators
from table_tools.ranker import ColumnStatistics, TableFrames
from table_tools.termination import end_search

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchConfig:
    """Limits for the discovery agent."""

    max_rounds: int = 6
    stagnation_limit: int = 3
    candidate_limit: int = 10


_DEFAULT_CANDIDATE_LIMIT = SearchConfig().candidate_limit
_EXISTENCE_POOL = 10
_VALUE_POOL = 300
_VALUE_RANK_LIMIT = 50


_ConstraintResolver = Callable[
    [list[QueryConstraint], str, dict[str, Any], list[Match]],
    list[QueryConstraint],
]


class DiscoveryAgent(AgentBase):
    """Discover tables with a fresh tree for each query."""

    def __init__(
        self,
        *,
        model: ChatModelBase,
        formatter: FormatterBase,
        frames: TableFrames,
        graph: RelationshipGraph,
        operators: TableOperators,
        matcher: ColumnNameMatcher,
        search: SearchConfig = SearchConfig(),
        schemas: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        super().__init__()
        self.name = "table_discovery"
        self.memory = InMemoryMemory()
        self.model = model
        self.formatter = formatter
        self._frames = frames
        self._graph = graph
        self._operators = operators
        self._matcher = matcher
        self._search = search
        self._schemas = (
            {
                table_id: list(frame.columns)
                for table_id, frame in frames.items()
            }
            if schemas is None
            else schemas
        )

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        """Store external messages in conversational memory."""
        if msg is not None:
            await self.memory.add(msg)

    async def reply(self, msg: Msg | list[Msg] | None = None) -> Msg:
        """Discover tables for the latest user query and return its matches."""
        await self.observe(msg)
        if msg is None:
            messages = await self.memory.get_memory()
        else:
            messages = [msg] if isinstance(msg, Msg) else msg
        user_message = next(
            (
                message
                for message in reversed(messages)
                if message.role == "user"
            ),
            None,
        )
        query = user_message.get_text_content() if user_message else None
        if not query or not query.strip():
            raise ValueError("A user message with a text query is required.")

        matches = await self.discover(query)
        content = (
            "\n".join(
                f"{match['table_id']}.{match['column_name']}"
                for match in matches
            )
            or "No matching tables found."
        )
        response = Msg(
            name=self.name,
            role="assistant",
            content=content,
            metadata={"matches": matches},
        )
        await self.memory.add(response)
        return response

    async def discover(
        self,
        query: str,
        seed_matches: Sequence[Match] | None = None,
    ) -> list[Match]:
        """Run bounded discovery, optionally starting from indexed matches."""
        if not query.strip():
            raise ValueError("The discovery query must contain text.")

        seeds = list(seed_matches or ())
        seed_schema: dict[str, None] = {}
        for seed in seeds:
            table_id = seed["table_id"]
            columns = self._schemas.get(table_id, [])
            if seed["column_name"] not in columns:
                raise ValueError(
                    f"Seed match refers to an unknown column in {table_id!r}.",
                )
            seed_schema.update(dict.fromkeys(columns))

        constraints = await extract_constraints(
            query,
            list(seed_schema),
            self.model,
            self.formatter,
        )
        state = DiscoveryState(seeds, initial_constraints=constraints)
        resolve = partial(
            resolve_constraints,
            frames=self._frames,
            matcher=self._matcher,
        )

        best_pending = None
        stagnant = 0
        for _ in range(self._search.max_rounds):
            node_id = _select_leaf(state, len(constraints))
            if node_id is None:
                break

            evidence = await self._observe(query, state, node_id)
            toolkit = create_planner_toolkit(state, node_id, self._operators)
            calls = await self._plan(query, state, node_id, evidence, toolkit)
            await execute_round(
                state,
                toolkit,
                node_id,
                calls,
                resolve=resolve,
            )

            # The first round establishes the unresolved-constraint baseline.
            pending = state.min_pending_constraints()
            if best_pending is None or pending < best_pending:
                best_pending = pending
                stagnant = 0
            else:
                stagnant += 1
                if stagnant >= self._search.stagnation_limit:
                    break

        return rank_results(
            state.collect_candidates(),
            constraints,
            self._frames,
            self._matcher,
        )

    async def _observe(
        self,
        query: str,
        state: DiscoveryState,
        node_id: str,
    ) -> dict | None:
        context = build_observation_context(
            state,
            node_id,
            self._graph,
            self._operators,
            self._frames,
            self._matcher,
            candidate_limit=self._search.candidate_limit,
            schemas=self._schemas,
        )
        return await summarize_observation(
            query,
            context,
            self.model,
            self.formatter,
        )

    async def _plan(
        self,
        query: str,
        state: DiscoveryState,
        node_id: str,
        evidence: dict | None,
        toolkit: Toolkit,
    ) -> list[ToolUseBlock]:
        return await plan_actions(
            query,
            state,
            node_id,
            evidence,
            toolkit,
            self.model,
            self.formatter,
            schemas=self._schemas,
            candidate_limit=self._search.candidate_limit,
        )


def _create_chat_backend(
    provider: Literal["qwen", "deepseek"],
    model_name: str,
    api_key: str,
) -> tuple[ChatModelBase, FormatterBase]:
    if provider == "qwen":
        return (
            DashScopeChatModel(
                model_name=model_name,
                api_key=api_key,
                stream=False,
                enable_thinking=False,
            ),
            DashScopeChatFormatter(),
        )
    if provider == "deepseek":
        return (
            OpenAIChatModel(
                model_name=model_name,
                api_key=api_key,
                stream=False,
                client_kwargs={"base_url": "https://api.deepseek.com"},
                generate_kwargs={
                    "extra_body": {"thinking": {"type": "disabled"}},
                },
            ),
            DeepSeekChatFormatter(),
        )
    raise ValueError("The chat provider must be qwen or deepseek.")


def run_query(
    index: ColumnIndex,
    question: str,
    model_name: str,
    api_key: str,
    *,
    provider: Literal["qwen", "deepseek"] = "qwen",
    frames: TableFrames,
    encoder: ColumnEncoder,
    search: SearchConfig = SearchConfig(),
    statistics: ColumnStatistics | None = None,
    graph: RelationshipGraph | None = None,
    schemas: Mapping[str, Sequence[str]] | None = None,
    key_sketch: Callable[[str, str], KeySketch] | None = None,
) -> str:
    """Run one discovery query with the selected chat provider."""
    try:
        model, formatter = _create_chat_backend(provider, model_name, api_key)
        if schemas is None:
            schemas = {
                table_id: list(frame.columns)
                for table_id, frame in frames.items()
            }
        matcher = ColumnNameMatcher(
            encoder,
            (name for columns in schemas.values() for name in columns),
        )
        if statistics is None:
            statistics = build_column_statistics(frames)
        if graph is None:
            graph = build_relationship_graph(
                index,
                frames,
                encoder,
                schemas=schemas,
                key_sketch=key_sketch,
            )
        operators = TableOperators(
            index,
            frames,
            statistics,
            matcher,
            schemas=schemas,
            key_sketch=key_sketch,
        )
        agent = DiscoveryAgent(
            model=model,
            formatter=formatter,
            frames=frames,
            graph=graph,
            operators=operators,
            matcher=matcher,
            search=search,
            schemas=schemas,
        )
        agent.set_console_output_enabled(False)
        response = asyncio.run(
            agent(Msg(name="user", content=question, role="user")),
        )
    except (DashScopeException, OpenAIError, RuntimeError) as error:
        message = str(error)
        if api_key:
            message = message.replace(api_key, "[redacted]")
        raise RuntimeError(message) from None
    answer = response.get_text_content()
    if not answer:
        raise RuntimeError("the discovery agent returned an empty response")
    return answer


@dataclass(frozen=True)
class ObservationEvidence:
    """Selected paths and schemas available to the next planning step."""

    paths: tuple[RelationshipPath, ...]
    schemas: dict[str, tuple[str, ...]]
    reachable_tables: tuple[str, ...]


def select_paths(
    paths: Sequence[RelationshipPath],
    footprint: set[str],
    path_budget: int = 6,
) -> list[RelationshipPath]:
    """Greedily cover tables beyond the footprint and normalize path scores."""
    remaining = list(paths)
    covered = footprint.copy()
    selected = []
    for _ in range(min(path_budget, len(remaining))):
        path = max(
            remaining,
            key=lambda item: (
                len(set(item.tables) - covered),
                item.reliability,
            ),
        )
        remaining.remove(path)
        selected.append(path)
        covered.update(path.tables)

    total = sum(path.reliability for path in selected)
    return [
        replace(
            path,
            normalized_score=path.reliability / total if total > 0 else 0.0,
        )
        for path in selected
    ]


def _tree_footprint(state: DiscoveryState, node_id: str) -> set[str]:
    """Collect candidates outside the selected node's subtree."""
    nodes = tuple(state.iter_nodes())
    children_by_parent: dict[str | None, list[str]] = defaultdict(list)
    for node in nodes:
        children_by_parent[node["parent_id"]].append(node["id"])

    subtree = {node_id}
    pending = [node_id]
    while pending:
        children = children_by_parent[pending.pop()]
        subtree.update(children)
        pending.extend(children)

    return {
        match["table_id"]
        for node in nodes
        if node["id"] not in subtree
        for match in node["matches"]
    }


def observe(
    graph: RelationshipGraph,
    state: DiscoveryState,
    node_id: str,
    seeds: Sequence[str],
    targets: Sequence[str],
    schemas: (
        Mapping[str, Sequence[str]] | Callable[[str], Sequence[str] | None]
    ),
    *,
    candidate_table_ids: Sequence[str] | None = None,
    max_depth: int = 3,
    path_pool_size: int = 40,
    path_budget: int = 6,
) -> ObservationEvidence:
    """Return structural evidence from supplied seeds and target tables.

    Raises:
        KeyError: If the discovery tree has no node with the supplied ID.
    """
    matches = state.get_matches(node_id)
    if candidate_table_ids is None:
        candidate_table_ids = [match["table_id"] for match in matches]
    candidates = dict.fromkeys(candidate_table_ids)
    paths = find_paths(graph, seeds, targets, max_depth, path_pool_size)
    selected = select_paths(
        paths,
        _tree_footprint(state, node_id),
        path_budget,
    )
    reachable = tuple(
        dict.fromkeys(
            table
            for path in selected
            for table in path.tables
            if table not in candidates
        ),
    )
    schema_for = schemas if callable(schemas) else schemas.get
    evidence_schemas = {}
    for table in (*candidates, *reachable):
        columns = schema_for(table)
        if columns is not None:
            evidence_schemas[table] = tuple(columns)
    return ObservationEvidence(tuple(selected), evidence_schemas, reachable)


def current_candidates(
    matches: list[Match],
    *,
    candidate_limit: int = _DEFAULT_CANDIDATE_LIMIT,
) -> list[Match]:
    """Return distinct tables by their best match score, up to the limit."""
    by_table: dict[str, Match] = {}
    for match in matches:
        table_id = match["table_id"]
        previous = by_table.get(table_id)
        if previous is None or match["score"] > previous["score"]:
            by_table[table_id] = match
    return sorted(by_table.values(), key=itemgetter("score"), reverse=True)[
        :candidate_limit
    ]


def _rank_values(
    operators: TableOperators,
    candidates: list[Match],
    constraint: QueryConstraint,
    values: list[Scalar],
) -> Iterator[Match]:
    name = constraint["col_name"]
    if constraint["col_type"] == "Categorical":
        for value in values:
            yield from operators.eq_ranker(
                candidates,
                name,
                value,
                result_cap=_VALUE_RANK_LIMIT,
            )
    else:
        lower, upper = cast(list[float | None], values)
        yield from operators.range_ranker(
            candidates,
            name,
            lower,
            upper,
            result_cap=_VALUE_RANK_LIMIT,
            allow_equal_bounds=True,
        )


def _find_targets(
    operators: TableOperators,
    constraints: list[QueryConstraint],
) -> dict[str, Match]:
    targets: dict[str, Match] = {}
    for constraint in constraints:
        values = constraint["values"]
        stage = "metadata search"
        try:
            pool = operators.metadata_seeker(
                [constraint["col_name"]],
                [constraint["col_type"]],
                result_cap=_VALUE_POOL if values else _EXISTENCE_POOL,
            )
            stage = "value ranking" if values else "result collection"
            matches = (
                _rank_values(operators, pool, constraint, values)
                if values
                else pool
            )
            for match in matches:
                targets.setdefault(match["table_id"], match)
        except Exception as error:
            # A failed search leaves the other constraints usable.
            _LOGGER.warning(
                "Target lookup failed for column %r during %s (%s)",
                constraint["col_name"],
                stage,
                type(error).__name__,
            )
    return targets


def build_observation_context(
    state: DiscoveryState,
    node_id: str,
    graph: RelationshipGraph,
    operators: TableOperators,
    frames: TableFrames,
    matcher: ColumnNameMatcher,
    *,
    candidate_limit: int = _DEFAULT_CANDIDATE_LIMIT,
    schemas: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Collect candidate schemas and diverse paths for observation."""
    node = state.get_node(node_id)
    candidates = current_candidates(
        node["matches"],
        candidate_limit=candidate_limit,
    )
    constraints = node["constraints"]
    targets = _find_targets(operators, constraints)
    initial = state.get_initial_constraints() or constraints

    seeds = []
    if initial:
        for match in candidates:
            table_id = match["table_id"]
            frame = frames.get(table_id)
            if frame is not None and any(
                satisfies(constraint, frame, matcher) for constraint in initial
            ):
                seeds.append(table_id)
    if not seeds:
        seeds = list(targets)[:candidate_limit]

    def schema_for(table_id: str) -> Sequence[str] | None:
        frame = frames.get(table_id)
        return list(frame.columns) if frame is not None else None

    evidence = observe(
        graph,
        state,
        node_id,
        seeds,
        list(targets),
        schema_for if schemas is None else schemas,
        candidate_table_ids=[match["table_id"] for match in candidates],
    )
    paths = []
    for index, path in enumerate(evidence.paths, 1):
        endpoint = path.tables[-1]
        paths.append(
            {
                "id": f"p{index}",
                "tables": list(path.tables),
                "endpoint": endpoint,
                "edges": [
                    {
                        "target": edge.target,
                        "kind": edge.kind,
                        "score": edge.score,
                        "columns": list(edge.columns),
                    }
                    for edge in path.edges
                ],
                "reliability": path.reliability,
                "normalized_score": path.normalized_score,
            },
        )

    return {
        "candidates": candidates,
        "schemas": {
            table: [str(name) for name in columns]
            for table, columns in evidence.schemas.items()
        },
        "constraints": [
            {"id": f"c{index}", **constraint}
            for index, constraint in enumerate(constraints, 1)
        ],
        "paths": paths,
        "reachable_tables": list(evidence.reachable_tables),
    }


async def _response(
    model: ChatModelBase,
    formatter: FormatterBase,
    system: str,
    content: str,
    *,
    tools: list[dict[str, Any]],
    tool_choice: Literal["none", "auto"],
) -> ChatResponse | None:
    messages = await formatter.format(
        [
            Msg(name="system", role="system", content=system),
            Msg(name="user", role="user", content=content),
        ],
    )
    response = await model(messages, tools=tools, tool_choice=tool_choice)
    if isinstance(response, AsyncIterable):
        final = None
        async for chunk in response:
            final = chunk
        return final
    return response


def _constraint_ids(values: list, known_ids: set[str]) -> list[str]:
    return list(
        dict.fromkeys(
            value
            for value in values
            if isinstance(value, str) and value in known_ids
        ),
    )


def _parse_observation(text: str, known_ids: set[str]) -> dict | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                parsed = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    if not isinstance(parsed, dict):
        return None

    directions = parsed.get("directions")
    stuck = parsed.get("stuck")
    if directions is None:
        directions = []
    if stuck is None:
        stuck = []
    if not isinstance(directions, list) or not isinstance(stuck, list):
        return None

    normalized = []
    for direction in directions[:4]:
        if not isinstance(direction, dict):
            return None
        related = direction.get("relates_to")
        if related is None:
            related = []
        if not isinstance(related, list):
            return None
        normalized.append(
            {
                **{
                    key: direction[key]
                    for key in ("id", "reaches", "via", "promise", "why")
                    if isinstance(direction.get(key), str)
                },
                "relates_to": _constraint_ids(related, known_ids),
            },
        )
    return {
        "directions": normalized,
        "stuck": _constraint_ids(stuck, known_ids),
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_observation_content(query: str, context: dict[str, Any]) -> str:
    """Format held tables, constraints, and paths for the observer."""
    constraints = context["constraints"]
    return OBSERVATION_TEMPLATE.format(
        query=query,
        candidates=_json(
            [match["table_id"] for match in context["candidates"]],
        ),
        schemas=_json(context["schemas"]),
        constraints=_json(constraints),
        paths=_json(context["paths"]),
    )


async def summarize_observation(
    query: str,
    context: dict,
    model: ChatModelBase,
    formatter: FormatterBase,
) -> dict | None:
    """Return structural directions or None after three invalid responses."""
    constraints = context["constraints"]
    known_ids = {constraint["id"] for constraint in constraints}
    user_content = build_observation_content(query, context)
    for attempt in range(3):
        response = await _response(
            model,
            formatter,
            OBSERVATION_SYS_PROMPT,
            user_content + (OBSERVATION_RETRY_HINT if attempt else ""),
            tools=[],
            tool_choice="none",
        )
        if response is None:
            continue
        text = "".join(
            block["text"]
            for block in response.content
            if block["type"] == "text"
        )
        evidence = _parse_observation(text, known_ids)
        if evidence is not None:
            return evidence
    return None


def _planner_error(message: str) -> ToolResponse:
    return ToolResponse(
        content=[TextBlock(type="text", text=message)],
        metadata={"error": message},
    )


def _planner_result(matches: list[Match]) -> ToolResponse:
    lines = [
        f"{match['table_id']}.{match['column_name']} "
        f"score={match['score']:.4f}"
        for match in matches
    ]
    return ToolResponse(
        content=[
            TextBlock(type="text", text="\n".join(lines) or "No matches."),
        ],
        metadata={"matches": matches},
    )


def create_planner_toolkit(
    state: DiscoveryState,
    node_id: str,
    operators: TableOperators,
) -> Toolkit:
    """Register the node-aware tools used by the discovery agent.

    The planner passes node IDs, which resolve to candidate tables.
    The available tools depend on the selected node.
    """
    ancestors = set(state.trajectory_ids(node_id))

    def matches_at(ref_id: str) -> list[Match]:
        ref_id = str(ref_id)
        try:
            referenced = state.get_node(ref_id)
        except KeyError:
            raise ValueError(f"Unknown node ID {ref_id!r}.") from None
        if referenced["error"] is not None:
            raise ValueError(f"Node {ref_id!r} recorded an error.")
        return referenced["matches"]

    def from_source(
        operator: Callable[..., list[Match]],
        src_node_id: str,
        *args: object,
    ) -> ToolResponse:
        src_node_id = str(src_node_id)
        try:
            matches = matches_at(src_node_id)
            if src_node_id not in ancestors:
                raise ValueError(
                    f"Source node {src_node_id!r} must be the selected node "
                    "or one of its ancestors.",
                )
            return _planner_result(operator(matches, *args))
        except ValueError as error:
            return _planner_error(str(error))

    def metadata_seeker(
        column_names: list[str],
        column_types: list[Literal["Categorical", "Numerical"]],
    ) -> ToolResponse:
        """Seed a branch with tables matching the requested column metadata.

        Use when the selected node has no candidates.

        Args:
            column_names: Requested column names or descriptions.
            column_types: Expected type of each column, in the same order.
        """
        if state.get_matches(node_id):
            return _planner_error(
                "Metadata search requires a node with no candidates.",
            )
        try:
            return _planner_result(
                operators.metadata_seeker(column_names, column_types),
            )
        except ValueError as error:
            return _planner_error(str(error))

    def eq_ranker(
        src_node_id: str,
        column_name: str,
        column_value: str,
    ) -> ToolResponse:
        """Rank candidate tables by how often a column contains a given value.

        Args:
            src_node_id: Selected node or ancestor supplying candidates.
            column_name: Categorical column to evaluate.
            column_value: Exact cell value, expressed as text.
        """
        return from_source(
            operators.eq_ranker,
            src_node_id,
            column_name,
            column_value,
        )

    def range_ranker(
        src_node_id: str,
        column_name: str,
        min_val: float | None,
        max_val: float | None,
    ) -> ToolResponse:
        """Rank candidate tables by how often a column falls within a range.

        Supply at least one bound.

        Args:
            src_node_id: Selected node or ancestor supplying candidates.
            column_name: Numerical column to evaluate.
            min_val: Inclusive lower bound, or null if unbounded.
            max_val: Inclusive upper bound, or null if unbounded.
        """
        return from_source(
            operators.range_ranker,
            src_node_id,
            column_name,
            min_val,
            max_val,
        )

    def join_search(src_node_id: str, join_column_name: str) -> ToolResponse:
        """Find related tables with overlapping values in a join column.

        Args:
            src_node_id: Selected node or ancestor supplying source tables.
            join_column_name: Column whose values identify matching rows.
        """
        return from_source(
            operators.join_search,
            src_node_id,
            join_column_name,
        )

    def union_search(
        src_node_id: str,
        union_column_names: list[str],
    ) -> ToolResponse:
        """Find related tables with columns similar to the source columns.

        Args:
            src_node_id: Selected node or ancestor supplying source tables.
            union_column_names: Source columns to match in other tables.
        """
        return from_source(
            operators.union_search,
            src_node_id,
            union_column_names,
        )

    def correlation_search(
        src_node_id: str,
        join_column_name: str,
        src_corr_column_name: str,
    ) -> ToolResponse:
        """Find tables with numerical measures correlated across shared keys.

        Use directly when the goal is correlation. This search aligns rows
        on the join column.

        Args:
            src_node_id: Selected node or ancestor supplying source tables.
            join_column_name: Source key column used to align rows.
            src_corr_column_name: Source numerical measure to compare.
        """
        return from_source(
            operators.correlation_search,
            src_node_id,
            join_column_name,
            src_corr_column_name,
        )

    def combine(
        node_id_1: str,
        node_id_2: str,
        set_op: Literal["intersection", "union", "difference"],
    ) -> ToolResponse:
        """Combine results from two existing nodes by table identity.

        Args:
            node_id_1: Node supplying the first result.
            node_id_2: Node supplying the second result.
            set_op: Keep shared tables with intersection, all tables with
                union, or tables exclusive to the first node with difference.
        """
        try:
            left, right = matches_at(node_id_1), matches_at(node_id_2)
        except ValueError as error:
            return _planner_error(str(error))

        normalized = set_op.strip().lower() if isinstance(set_op, str) else ""
        operation: Literal["intersection", "union", "difference"]
        if normalized == "union":
            operation = "union"
        elif normalized == "difference":
            operation = "difference"
        else:
            operation = "intersection"
        response = combine_results(left, right, operation)
        metadata = response.metadata or {}
        if "error" in metadata:
            return response
        return _planner_result(metadata["matches"][: operators.result_cap])

    toolkit = Toolkit()
    toolkit.create_tool_group(
        "metadata",
        "Seed the branch when the selected node has no candidates.",
        active=not state.get_matches(node_id),
    )
    toolkit.register_tool_function(metadata_seeker, group_name="metadata")
    for tool in (
        eq_ranker,
        range_ranker,
        join_search,
        union_search,
        correlation_search,
        combine,
        end_search,
    ):
        toolkit.register_tool_function(tool)
    return toolkit


def _operation(node: _Node) -> dict[str, Any]:
    entry = {
        "node_id": node["id"],
        "parent_id": node["parent_id"],
        "tool": node["tool_name"],
        "input": node["inputs"],
        "matches": len(node["matches"]),
    }
    error = node["error"]
    if error is not None:
        entry["error"] = " ".join(error.split())[:200]
    return entry


def build_planning_content(
    query: str,
    state: DiscoveryState,
    node_id: str,
    evidence: dict | None,
    schemas: Mapping[str, Sequence[str]],
    candidates: list[Match],
) -> str:
    """Format the current node, candidate schemas, and operation history."""
    nodes = {node["id"]: node for node in state.iter_nodes()}
    current = nodes[node_id]
    ancestor_ids = state.trajectory_ids(node_id)

    trajectory = [
        _operation(nodes[ancestor_id])
        for ancestor_id in reversed(ancestor_ids)
        if nodes[ancestor_id]["tool_name"] is not None
    ]
    tree_history = {}
    failures = []
    for node in nodes.values():
        if node["id"] in ancestor_ids or node["tool_name"] is None:
            continue
        if node["error"] is not None:
            failures.append(_operation(node))
        else:
            signature = (
                node["tool_name"],
                json.dumps(node["inputs"], sort_keys=True),
            )
            tree_history.setdefault(signature, _operation(node))

    candidate_rows = [
        {
            "table_id": match["table_id"],
            "schema": list(
                schemas.get(match["table_id"], (match["column_name"],)),
            ),
            "score": match["score"],
        }
        for match in candidates
    ]
    constraints = [
        {"id": f"c{index}", **constraint}
        for index, constraint in enumerate(current["constraints"], start=1)
    ]
    return PLANNING_TEMPLATE.format(
        query=query,
        node_id=node_id,
        source_ids=_json(
            [
                ancestor_id
                for ancestor_id in ancestor_ids
                if nodes[ancestor_id]["error"] is None
            ],
        ),
        combine_ids=_json(
            [node["id"] for node in nodes.values() if node["error"] is None],
        ),
        candidates=_json(candidate_rows),
        constraints=_json(constraints),
        evidence=(
            "Observation evidence unavailable."
            if evidence is None
            else _json(evidence)
        ),
        trajectory=_json(trajectory),
        tree_history=_json(list(tree_history.values())[-20:]),
        failures=_json(failures[-10:]),
    )


async def plan_actions(
    query: str,
    state: DiscoveryState,
    node_id: str,
    evidence: dict | None,
    toolkit: Toolkit,
    model: ChatModelBase,
    formatter: FormatterBase,
    *,
    schemas: Mapping[str, Sequence[str]] | None = None,
    candidate_limit: int = _DEFAULT_CANDIDATE_LIMIT,
) -> list[ToolUseBlock]:
    """Ask the planner for tool calls without executing them."""
    candidates = current_candidates(
        state.get_matches(node_id),
        candidate_limit=candidate_limit,
    )
    user_content = build_planning_content(
        query,
        state,
        node_id,
        evidence,
        schemas or {},
        candidates,
    )
    tools = toolkit.get_json_schemas()
    for attempt in range(3):
        response = await _response(
            model,
            formatter,
            PLANNING_SYS_PROMPT,
            user_content + (PLANNING_RETRY_HINT if attempt else ""),
            tools=tools,
            tool_choice="auto",
        )
        if response is None:
            continue
        calls = [
            cast(ToolUseBlock, block)
            for block in response.content
            if block["type"] == "tool_use"
        ]
        if calls:
            return calls
    return []


async def _execute_call(
    toolkit: Toolkit,
    call: ToolUseBlock,
    parent_matches: list[Match],
) -> tuple[list[Match], bool, str | None]:
    response: ToolResponse | None = None
    async for chunk in await toolkit.call_tool_function(call):
        response = chunk
    if response is None:
        return [], False, "The tool returned no response."

    metadata = response.metadata or {}
    if "error" in metadata:
        return [], False, str(metadata["error"])
    if metadata.get("end_search"):
        return deepcopy(parent_matches), True, None
    if "matches" in metadata:
        return cast(list[Match], metadata["matches"]), False, None

    error = "\n".join(
        block["text"] for block in response.content if block["type"] == "text"
    ).strip()
    return [], False, error or "The tool returned no discovery result."


async def execute_round(
    state: DiscoveryState,
    toolkit: Toolkit,
    node_id: str,
    calls: Sequence[ToolUseBlock],
    *,
    resolve: _ConstraintResolver | None = None,
) -> list[str]:
    """Run eligible calls in order and return the IDs of their children."""
    parent = state.get_node(node_id)
    if parent["ended"]:
        return []

    parent_matches = parent["matches"]
    children: list[str] = []
    for call in calls:
        name, inputs = call["name"], call["input"]
        # The standalone seeker seeds branches with no candidates.
        if name in ("seek_columns", "metadata_seeker") and parent_matches:
            continue
        if name != "end_search" and state.already_tried(name, inputs):
            continue

        remaining = None
        try:
            matches, terminated, error = await _execute_call(
                toolkit,
                call,
                parent_matches,
            )
            if error is None and resolve is not None:
                remaining = resolve(
                    deepcopy(parent["constraints"]),
                    name,
                    inputs,
                    matches,
                )
        except Exception as exception:
            matches = []
            terminated = False
            error = str(exception) or type(exception).__name__

        children.append(
            state.add_child(
                node_id,
                name,
                inputs,
                matches,
                constraints=remaining,
                terminated=terminated,
                error=error,
            ),
        )
    return children


def _select_leaf(state: DiscoveryState, initial_count: int) -> str | None:
    def priority(leaf: tuple[str, int, int]) -> tuple[float, int, int]:
        _, depth, pending = leaf
        progress = (initial_count - pending) / depth if depth else inf
        return progress, -pending, depth

    leaf = max(state.iter_active_leaves(), key=priority, default=None)
    return None if leaf is None else leaf[0]
