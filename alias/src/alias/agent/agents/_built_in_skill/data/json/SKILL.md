---
name: json-file
description: Guildlines for handling json files
type: json
---

# JSON Handling Specifications

## Goals
- Safely parse JSON/JSONL without memory overflow.
- Discover schema structure (keys, nesting depth, data types).
- Flatten complex nested structures into tabular data when necessary.
- Handle inconsistent schemas and "dirty" JSON (e.g., trailing commas, mixed types).

## Inspection (Always First)

- Structure Discovery:
  - Determine if the root is a `list` or a `dict`.
  - Identify if it's a standard JSON or JSONL (one valid JSON object per line).
- Schema Sampling:
  - For large files, read the first few objects/lines to infer the schema.
  - Identify top-level keys and their types.
  - Detect nesting depth: If depth > 3, consider it a "deeply nested" structure.
- Size Check:
  - If the file is large (>50MB), avoid `json.load()`. Use iterative parsing or streaming.

## Processing & Extraction

- Lazy Loading (Streaming):
  - For massive JSON: Use `ijson` (Python) or similar streaming parsers to yield specific paths/items.
  - For JSONL: Read line-by-line using a generator to minimize memory footprint.
- Flattening & Normalization:
  - Use `pandas.json_normalize` to convert nested structures into flat tables if the goal is analysis.
  - Specify `max_level` during normalization to prevent "column explosion."
- Data Filtering:
  - Extract only required sub-trees (keys) early in the process to reduce the memory object size.

## Data Quality & Schema Validation

- Missing Keys: Use `.get(key, default)` or `try-except` blocks. Never assume a key exists in all objects.
- Type Coercion:
  - Validate numeric strings vs. actual numbers.
  - Standardize `null`, `""`, and `[]` consistently.
- Encoding: Default to UTF-8; check for BOM (utf-8-sig) if parsing fails.
- Malformed JSON Recovery:
  - For minor syntax errors (e.g., single quotes instead of double), attempt `ast.literal_eval` or regex-based cleanup only as a fallback.

## Best Practices

- Minimal Reads: Don't load a 50MB JSON just to read one config key; use a streaming approach.
- Schema Logging: Document the detected structure (e.g., "Root is a list of 500 objects; key 'metadata' is nested").
- Error Transparency: When a JSON object in a JSONL stream is corrupted, log the line number, skip it, and continue instead of crashing the entire process.
- Avoid Over-Flattening: Be cautious with deeply nested arrays; flattening them can lead to massive row duplication.
- Strict Typing: After extraction, explicitly convert types (e.g., `pd.to_datetime`) to ensure downstream reliability.
