// src/viewers/styles.ts

export const COMMON_STYLES = `
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

    /* Horizontal line */
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

    /* Image styles */
    img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 1em 0;
    }

    /* Paragraph styles */
    p {
        margin-top: 0;
        margin-bottom: 16px;
    }

    /* Emphasis styles */
    em {
        font-style: italic;
    }

    strong {
        font-weight: bold;
    }

    /* Strikethrough styles */
    del {
        text-decoration: line-through;
    }

    /* Superscript and subscript */
    sup, sub {
        font-size: 75%;
        line-height: 0;
        position: relative;
        vertical-align: baseline;
    }

    sup {
        top: -0.5em;
    }

    sub {
        bottom: -0.25em;
    }

    /* Keyboard input styles */
    kbd {
        background-color: #fafbfc;
        border: 1px solid #d1d5da;
        border-bottom-color: #c6cbd1;
        border-radius: 3px;
        box-shadow: inset 0 -1px 0 #c6cbd1;
        color: #444d56;
        display: inline-block;
        font-size: 11px;
        line-height: 10px;
        padding: 3px 5px;
        vertical-align: middle;
    }

    /* Text selection styles */
    ::selection {
        background: #b3d4fc;
        text-shadow: none;
    }

    /* Scrollbar styles */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
`;

export const HIGHLIGHT_STYLES = {
  tomorrow: {
    "hljs-comment": {
      color: "#999999",
    },
    "hljs-keyword": {
      color: "#cc99cd",
    },
    "hljs-string": {
      color: "#7ec699",
    },
  },
};
