---
name: database
description: Guidelines for handling databases
type: relational_db
---

# Database Handling Specifications

## Goals

- Safely explore database schema without performance degradation.
- Construct precise, efficient SQL queries that prevent system crashes (OOM & OOT).
- Handle dialect-specific nuances (PostgreSQL, MySQL, SQLite, etc.).
- Transform raw result sets into structured, validated data for analysis.

## Inspection

- Volume Estimation:
  - Before any `SELECT *`, always run `SELECT COUNT(*) FROM table_name` to understand the scale.
  - If a table has >1,000,000 rows, strictly use indexed columns for filtering.
- Sample Data:
  - Use `SELECT * FROM table_name LIMIT 5` to see actual data formats.

## Querying

- Safety Constraints:
  - Always use `LIMIT`: Never execute a query without a `LIMIT` clause unless the row count is confirmed to be small.
  - Avoid `SELECT *`: In production-scale tables, explicitly name columns to reduce I/O and memory usage.
- Dialect & Syntax:
  - Case Sensitivity: If a column/table name contains uppercase or special characters, MUST quote it (e.g., `"UserTable"` in Postgres, `` `UserTable` `` in MySQL).
  - Date/Time: Use standard ISO strings for date filtering; be mindful of timezone-aware vs. naive columns.
- Complex Queries:
  - For `JOIN` operations, ensure joining columns are indexed to prevent full table scans.
  - When performing `GROUP BY`, ensure the result set size is manageable.

## Data Retrieval & Transformation

- Type Mapping:
  - Ensure SQL types (e.g., `DECIMAL`, `BIGINT`, `TIMESTAMP`) are correctly mapped to Python/JSON types without precision loss.
  - Convert `NULL` values to a consistent "missing" representation (e.g., `None` or `NaN`).
- Chunked Fetching:
  - For medium-to-large exports, use `fetchmany(size)` or `OFFSET/LIMIT` pagination instead of fetching everything into memory at once.
- Aggregations:
  - Prefer performing calculations (SUM, AVG, COUNT) at the database level rather than pulling raw data to the client for processing.

## Error Handling & Recovery

- Timeout Management: If a query takes too long, retry with more restrictive filters or optimized joins.
- Syntax Errors: If a query fails, inspect the dialect-specific error message and re-verify the schema (it's often a misspelled column or missing quotes).

## Anti-Pattern Prevention (Avoiding "Bad" SQL)

- Index-Friendly Filters: Never wrap indexed columns in functions (e.g., `DATE()`, `UPPER()`) within the `WHERE` clause.
- Join Safety: Always verify join keys. Before joining, check if the key has high cardinality to avoid massive intermediate result sets.
- Memory Safety:
  - Avoid `DISTINCT` and `UNION` (which performs de-duplication) on multi-million row sets unless necessary; use `UNION ALL` if duplicates are acceptable.
  - Avoid `ORDER BY` on large non-indexed text fields.
- Wildcard Warning: Strictly avoid leading wildcards in `LIKE` patterns (e.g., `%term`) on large text columns.
- No Function on Columns: `WHERE col = FUNC(val)` is good; `WHERE FUNC(col) = val` is bad.
- Explicit Columns: Only fetch what is necessary.
- Early Filtering: Push `WHERE` conditions as close to the base tables as possible.
- CTE for Clarity: Use `WITH` for complex multi-step logic to improve maintainability and optimizer hints.

# Best Practices

- Always verify database structure before querying
- Use appropriate sampling techniques for large datasets
- Optimize queries for efficiency based on schema inspection
- Self-review the draft SQL against the "Anti-Pattern Prevention" list.
- Perform a silent mental 'EXPLAIN' on your query. If it smells like a full table scan on a large table, refactor it before outputting
