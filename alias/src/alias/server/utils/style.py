# -*- coding: utf-8 -*-
# flake8: noqa: E501
# pylint: disable=consider-using-f-string
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

COMMON_CSS = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        color: #333;
        line-height: 1.6;
        padding: 30px;
        max-width: 900px;
        margin: 0 auto;
        background-color: #ffffff;
    }

    /* Markdown heading styles */
    h1, h2, h3, h4, h5, h6 {
        position: relative;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-weight: bold;
        line-height: 1.4;
        cursor: text;
        color: #2c3e50;
    }

    h1 {
        font-size: 2.25em;
        border-bottom: 1px solid #eceff1;
        padding-bottom: 0.3em;
    }

    h2 {
        font-size: 1.75em;
        border-bottom: 1px solid #eceff1;
        padding-bottom: 0.3em;
    }

    h3 {
        font-size: 1.5em;
    }

    h4 {
        font-size: 1.25em;
    }

    h5 {
        font-size: 1em;
    }

    h6 {
        font-size: 1em;
        color: #777;
    }

    /* Code block styles */
    pre {
        background-color: #f8f8f8;
        border-radius: 3px;
        padding: 10px;
        font-size: 0.9em;
        line-height: 1.5;
        overflow-x: auto;
        border: 1px solid #e9e9e9;
    }

    code {
        font-family: 'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace;
        background-color: rgba(0,0,0,0.05);
        padding: 0.2em 0.4em;
        margin: 0;
        border-radius: 3px;
        font-size: 85%;
    }

    pre code {
        background-color: transparent;
        padding: 0;
        margin: 0;
        border-radius: 0;
        font-size: 100%;
    }

    /* Table styles */
    table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 1.5em;
        display: block;
        overflow-x: auto;
    }

    table tr {
        background-color: #fff;
        border-top: 1px solid #c6cbd1;
    }

    table tr:nth-child(2n) {
        background-color: #f6f8fa;
    }

    table th,
    table td {
        padding: 10px 15px;
        border: 1px solid #dfe2e5;
    }

    table th {
        font-weight: bold;
        background-color: #f0f0f0;
        text-align: left;
    }

    /* Blockquote styles */
    blockquote {
        border-left: 4px solid #dfe2e5;
        padding: 0 15px;
        color: #777;
        margin: 0;
    }

    /* List styles */
    ul, ol {
        padding-left: 30px;
        margin-top: 0;
        margin-bottom: 16px;
    }

    /* Link styles */
    a {
        color: #0366d6;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    /* Horizontal rule */
    hr {
        border: 0;
        height: 1px;
        background-color: #e1e4e8;
        margin: 16px 0;
    }

    /* Additional styles for inline code and code blocks */
    .highlight {
        background-color: #f8f8f8;
        border-radius: 3px;
    }

    .linenos {
        background-color: #f0f0f0;
        padding-right: 10px;
        text-align: right;
        color: #999;
    }
</style>
"""


def get_pygments_css(style="colorful"):
    """
    Get Pygments syntax highlighting CSS styles.

    :param style: Highlighting style name, defaults to 'colorful'.
    :return: CSS style string.
    """
    return HtmlFormatter(style=style).get_style_defs(".highlight")


def highlight_code(content, lexer_name, style="colorful"):
    """
    Apply syntax highlighting to code using Pygments.

    :param content: Code content to highlight.
    :param lexer_name: Lexer name for the programming language.
    :param style: Highlighting style, defaults to 'colorful'.
    :return: HTML code with syntax highlighting.
    """
    try:
        lexer = get_lexer_by_name(lexer_name)
        formatter = HtmlFormatter(
            linenos="table",
            style=style,
            cssclass="highlight",
        )
        highlighted_code = pygments.highlight(content, lexer, formatter)
        return highlighted_code
    except Exception:
        return f"<pre>{content}</pre>"


def create_html_preview(title, content, extra_css=""):
    """
    Create a generic HTML preview page.

    :param title: Page title.
    :param content: Page content.
    :param extra_css: Additional CSS styles.
    :return: Complete HTML string.
    """
    return f"""
    <html>
    <head>
        <title>{title}</title>
        {COMMON_CSS}
        <style>{get_pygments_css()}</style>
        {extra_css}
    </head>
    <body>
        {content}
    </body>
    </html>
    """


def render_markdown(md_content):
    """
    Render Markdown content to HTML.

    :param md_content: Markdown text.
    :return: Converted HTML.
    """
    import markdown2

    html_content = markdown2.markdown(
        md_content,
        extras=[
            "code-friendly",
            "fenced-code-blocks",
            "tables",
            "cuddled-lists",
            "header-ids",
        ],
    )

    return html_content


def render_csv_to_html(csv_content):
    """
    Convert CSV content to an HTML table.

    :param csv_content: CSV text content.
    :return: HTML table string.
    """
    import csv
    from io import StringIO

    csv_reader = csv.reader(StringIO(csv_content))
    headers = next(csv_reader)
    table_html = (
        "<table><thead><tr>{}</tr></thead><tbody>{}</tbody></table>".format(
            "".join(f"<th>{header}</th>" for header in headers),
            "".join(
                f"<tr>{''.join(f'<td>{item}</td>' for item in row)}</tr>"
                for row in csv_reader
            ),
        )
    )

    return table_html


def sanitize_html(html_content):
    """
    Basic HTML sanitization.
    """
    # TODO: avoid xss attack!!!
    return html_content
