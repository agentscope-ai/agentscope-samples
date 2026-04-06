---
name: text-file
description: Guidelines for handling text files
type: text
---

# Text Files Handling Specifications

## Goals
- Safely read text files without memory exhaustion.
- Accurately detect encoding to avoid garbled characters.
- Identify underlying patterns (e.g., Log formats, Markdown structure, delimiters).
- Efficiently extract or search for specific information within large volumes of text.

## Encoding & Detection

- Encoding Strategy:
  - Default to `utf-8`.
  - If it fails, try `utf-8-sig` (for files with BOM), `gbk/gb18030` (for Chinese context), or `latin-1`.
  - Use `chardet` or similar logic if encoding is unknown and first few bytes look non-standard.
- Line Endings: Be aware of `\n` (Unix), `\r\n` (Windows), and `\r` (Legacy Mac) when counting lines or splitting.

## Inspection

- Preview: Read the first 10-20 lines to determine:
  - Content Type: Is it a log, code, prose, or a semi-structured list?
  - Uniformity: Does every line follow the same format?
- Metadata: Check total file size before reading. If >50MB, treat as a "large file" and avoid full loading.

## Querying & Reading (Large Files)

- Streaming: For files exceeding memory or >50MB:
  - Use `with open(path) as f: for line in f:` to process line-by-line.
  - Never use `.read()` or `.readlines()` on large files.
- Random Sampling: To understand a huge file's structure, read the first N lines, the middle N lines (using `f.seek()`), and the last N lines.
- Pattern Matching: Use Regular Expressions (Regex) for targeted extraction instead of complex string slicing.
- Grep-like Search: If searching for a keyword, iterate through lines and only store/return matching lines + context.

## Data Quality

- Truncation Warning: If only a portion of the file is read, clearly state: "Displaying first X lines of Y total lines."
- Empty Lines/Comments: Decide early whether to ignore blank lines or lines starting with specific comment characters (e.g., `#`, `//`).

## Best Practices

- Resource Safety: Always use context managers (`with` statement) to ensure file handles are closed.
- Memory Consciousness: For logs and large TXT, prioritize "find and extract" over "load and filter."
- Regex Optimization: Compile regex patterns if they are used repeatedly in a loop over millions of lines.
- Validation: After reading, verify the content isn't binary (e.g., PDF or EXE renamed to .txt) by checking for null bytes or a high density of non-ASCII characters.
- Progress Logging: For long-running text processing, log progress every 100k lines or 10% of file size.
