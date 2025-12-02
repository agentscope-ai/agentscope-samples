# -*- coding: utf-8 -*-
import json
import mimetypes

from io import BytesIO

from typing import Tuple
import chardet


from alias.server.utils.style import (
    create_html_preview,
    highlight_code,
    render_csv_to_html,
    render_markdown,
    sanitize_html,
)


def preview_file(file_path, file_ext, raw_data) -> Tuple[BytesIO, str]:
    media_type = mimetypes.guess_type(file_path)[0] or "text/plain"
    encoding = chardet.detect(raw_data)["encoding"] or "utf-8"

    try:
        content = raw_data.decode(encoding)
    except UnicodeDecodeError:
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_data.decode(encoding, errors="ignore")

    preview_handlers = {
        "html": lambda: sanitize_html(content),
        "md": lambda: create_html_preview(
            "Markdown Preview",
            render_markdown(content),
        ),
        "txt": lambda: create_html_preview(
            "Text Preview",
            f"<pre>{content}</pre>",
        ),
        "json": lambda: create_html_preview(
            "JSON Preview",
            highlight_code(
                json.dumps(json.loads(content), indent=4),
                "json",
            ),
        ),
        "csv": lambda: create_html_preview(
            "CSV Preview",
            render_csv_to_html(content),
        ),
        "xml": lambda: create_html_preview(
            "XML Preview",
            highlight_code(content, "xml"),
        ),
        "yaml": lambda: create_html_preview(
            "YAML Preview",
            highlight_code(content, "yaml"),
        ),
        "yml": lambda: create_html_preview(
            "YAML Preview",
            highlight_code(content, "yaml"),
        ),
        "log": lambda: create_html_preview(
            "Log Preview",
            highlight_code(content, "text"),
        ),
    }

    if file_ext in preview_handlers:
        html_content_bytes = preview_handlers[file_ext]().encode("utf-8")
        return BytesIO(html_content_bytes), "text/html"

    return BytesIO(raw_data), media_type
