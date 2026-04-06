---
name: csv-excel-file
description: Guidelines for handling CSV/Excel files
type:
  - csv
  - excel
---

# CSV/Excel Handling Specifications

## Goals

- Safely load tabular data without crashing.
- Detect and handle messy spreadsheets (multiple blocks, missing headers, merged cells artifacts).
- Produce reliable outputs (clean dataframe for clean table or structured JSON for messy spreadsheet) with validated types.

## Encoding, Delimiters, and Locale

- CSV encoding: Try UTF-8; if garbled, attempt common fallbacks (e.g., gbk, cp1252) based on context.
- Delimiters: Detect common separators (,, \t, ;, |) during inspection.
- Locale formats: Be cautious with comma decimal separators and thousands separators.

## Inspection (always first)

- Identify file type, encoding (CSV), and sheet names (Excel) before full reads.
- Prefer small reads to preview structure:
  - CSV: pd.read_csv(..., nrows=20); if uncertain delimiter: sep=None, engine="python" (small nrows only).
  - Excel: pd.ExcelFile(path).sheet_names, then pd.read_excel(..., sheet_name=..., nrows=20).
- Use df.head(n) and df.columns to check:
  - Missing/incorrect headers (e.g., columns are numeric 0..N-1)
  - "Unnamed: X" columns
  - Unexpected NaN/NaT, merged-cell artifacts
  - Multiple tables/blocks in one sheet (blank rows separating sections)

## Preprocessing

- Treat as messy if any of the following is present:
  - Columns contain "Unnamed:" or mostly empty column names
  - Header row appears inside the data (first rows look like data + later row looks like header)
  - Multiple data blocks (large blank-row gaps, repeated header patterns)
  - Predominantly NaN/NaT in top rows/left columns
  - Notes/metadata blocks above/beside the table (titles, footnotes, merged header areas)
- If messy spreadsheets are detected:
  - First choice: use  `clean_messy_spreadsheet` tool to extract key tables/fields and output JSON.
  - Only fall back to manual parsing if tool fails, returns empty/incorrect structure, or cannot locate the target table.

## Querying

- Never load entire datasets blindly.
- Use minimal reads:
  - `nrows`, `usecols`, `dtype` (or partial dtype mapping), `parse_dates` only when necessary.
  - Sampling: `skiprows` with a step pattern for rough profiling when file is huge.
- For very large CSV:
  - Prefer `chunksize` iteration; aggregate/compute per chunk.
- For Excel:
  - Read only needed `sheet_name`, and consider narrowing `usecols`/`nrows` during exploration.

## Data Quality & Type Validation

- After load/clean:
  - Validate types:
    - Numeric columns: coerce with pd.to_numeric(errors="coerce")
    - Datetime columns: pd.to_datetime(errors="coerce")
  - Report coercion fallout (how many became NaN/NaT).
  - Standardize missing values: treat empty strings/“N/A”/“null” consistently.

# Best Practices

- Always inspect structure before processing.
- Handle encoding issues appropriately
- Keep reads minimal; expand only after confirming layout.
- Log decisions: chosen sheet, detected header row, dropped columns/rows, dtype conversions.
- Avoid silent data loss: when dropping/cleaning, summarize what changed.
- Validate data types after loading
