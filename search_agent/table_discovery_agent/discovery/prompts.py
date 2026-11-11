# -*- coding: utf-8 -*-
"""Prompts for constraint extraction, observation, and discovery planning."""

COL_CONSTRAINT_PROMPT = """## Task
Extract the column requirements from the query.

## Rules
- Identify named columns used in relationships, filters, measures, or
  results. Use the optional query table schema for context. Omit vague
  references such as "a related metric".
- Include a year or age bracket in `col_name` when it identifies the
  column.
- Use an empty `values` array when only column presence is required.
- List required cell values for categorical conditions.
- Use an inclusive `[lower, upper]` range for numerical conditions. Use
  `null` for one open bound. Two finite bounds must be distinct.
- For "about N", use a range of 10% of |N| on each side of N.
- Express bounds in the column's units. For example, use 206 for
  "206 thousand" in `population_thousands`.

## Output
Return only a JSON array. Each object has exactly these fields.

- `col_name` is a string.
- `col_type` is "Categorical" or "Numerical".
- `values` is an array.

[
  {{"col_name": "region", "col_type": "Categorical", "values": []}},
  {{"col_name": "team", "col_type": "Categorical", "values": ["Ferrari"]}},
  {{"col_name": "population", "col_type": "Numerical",
    "values": [30000, null]}}
]

## Query
{query}

## Query Table Schema
{table_schema}
"""

CONSTRAINT_RETRY_HINT = (
    "\nThe previous response was invalid. Return only a JSON array "
    "with the required fields and values."
)


OBSERVATION_SYS_PROMPT = """## Task
Summarize what the observed paths reach and how the tables connect.

## Rules
- Group paths that share a bridge and have similar endpoint schemas.
- Use endpoint columns to identify which unresolved constraints each
  group supports. Value conditions provide column context. Leave value
  checks and tool selection to the planner.
- Rank directions by relevance and report up to four. Rate each direction
  using query relevance and path reliability.

## Output
Return only a JSON object with two arrays.

- `directions` contains one object per reported group. Each object has
  `id`, `reaches` (notable endpoint columns), `via` (shared key or
  columns), `relates_to` (supported constraint IDs), `promise` ("high",
  "medium", or "low"), and `why` (one sentence explaining the rating).
  These fields are strings, except `relates_to`, which is an array of IDs.
- `stuck` contains constraint IDs that no observed path reaches.
"""

OBSERVATION_TEMPLATE = """## Query
{query}

## Unresolved Constraints
{constraints}

## Held Candidate Tables
{candidates}

## Observed Paths
{paths}

## Table Schemas
{schemas}
"""

OBSERVATION_RETRY_HINT = (
    "\n\nThe previous response was invalid. Return only a JSON object "
    "with directions and stuck arrays."
)


PLANNING_SYS_PROMPT = """## Task
Choose tools that advance the current step of the user's query.

## Rules

### Identify the current step
- Follow the query's stated order and relationships.
- Check held tables and unresolved constraints to identify what is missing.
- Check for unfinished steps even when no constraints remain.

### Choose the next action
- Start with metadata_seeker when the node has no candidates.
- Apply current-step value conditions with eq_ranker or range_ranker.
  Use distinct finite bounds and null for an open range bound.
- Expand through the requested relationship after applying value conditions.
  Use join_search, union_search, or correlation_search with the relevant
  source columns. Use correlation_search directly for correlation.
- Use combine when existing results need to be merged.
  For alternatives, explore both branches before combining with union.

### Preserve results and continue
- Use end_search to preserve eligible results from a completed step.
  Later steps may still have unresolved constraints.
- If another step follows, call end_search and the next relationship tool
  together. Both calls create siblings from the current node.
- Finish the last applicable step with end_search.
  The bare query-table root is ineligible as a result.

### Check the calls
- Follow tool definitions and use only the allowed node IDs.
  Reference new children in a later turn.
- Avoid repeating identical calls across the tree.
  Use end_search on distinct branches as needed.
- Correct failed arguments before retrying.

## Output
Return tool calls for the next action.
"""

PLANNING_TEMPLATE = """## Query
{query}

## Current Node
{node_id}

## Held Candidate Tables
{candidates}

## Unresolved Constraints
{constraints}

## Observation Evidence
{evidence}

## Allowed Node IDs
- Source node arguments: {source_ids}
- Combine arguments: {combine_ids}

## Current Trajectory
{trajectory}

## Tree-Wide Operations Already Tried
{tree_history}

## Failed Tool Calls on Other Branches
{failures}
"""

PLANNING_RETRY_HINT = (
    "\n\nThe previous response contained no tool call. Call a tool to "
    "advance the query or call end_search if the current step is complete."
)
