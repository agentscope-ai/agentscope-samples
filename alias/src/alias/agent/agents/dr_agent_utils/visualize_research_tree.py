#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-many-branches line-too-long unused-argument W0612 E0611 C2801 R0915
# flake8: noqa: E501
"""
Research Tree Visualizer
Visualize tree-based research agent's exploration process with professional aesthetics.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def load_tree_json(file_path: str) -> Dict[str, Any]:
    """Load research tree from JSON file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_tree_stats(node: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistics about the research tree"""

    def traverse(n, depth=1):
        # Check if terminated/abandoned based on status or evaluation_details
        status = n.get("status", "")
        eval_details = n.get("evaluation_details", {})
        # Check new format first (current_status), then fall back to old format (task_done)
        current_status = (
            eval_details.get("current_status", "").lower()
            if eval_details.get("current_status")
            else ""
        )
        task_done = eval_details.get("task_done")
        is_terminated = status == "abandoned" or (
            current_status == "abandoned"
            or current_status == "terminated"
            or (isinstance(task_done, bool) and task_done is False)
        )
        is_completed = status == "done" or (
            current_status == "done"
            or current_status == "completed"
            or (isinstance(task_done, bool) and task_done is True)
        )

        # Count info items from node_report and auxiliary_info
        node_report = n.get("node_report", "")
        auxiliary_info = n.get("auxiliary_info", {})
        info_count = (1 if node_report else 0) + (
            1 if auxiliary_info and len(auxiliary_info) > 0 else 0
        )

        stats = {
            "total_nodes": 1,
            "max_depth": depth,
            "total_iterations": 0,  # attempt field no longer used
            "total_info_items": info_count,
            "terminated_nodes": 1 if is_terminated else 0,
            "completed_nodes": 1 if is_completed else 0,
        }

        for child in n.get("decomposed", []):
            child_stats = traverse(child, depth + 1)
            stats["total_nodes"] += child_stats["total_nodes"]
            stats["max_depth"] = max(
                stats["max_depth"],
                child_stats["max_depth"],
            )
            stats["total_iterations"] += child_stats["total_iterations"]
            stats["total_info_items"] += child_stats["total_info_items"]
            stats["terminated_nodes"] += child_stats["terminated_nodes"]
            stats["completed_nodes"] += child_stats["completed_nodes"]

        return stats

    return traverse(node)


def print_terminal_tree(
    node: Dict[str, Any],
    indent: int = 0,
    is_last: bool = True,
    prefix: str = "",
):
    """Print a beautiful terminal tree view"""

    # Color codes
    # BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    # RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"

    # Node info
    node_id = node.get("id", node.get("node_id", "unknown"))
    name = node.get("name", "")
    description = node.get(
        "description",
        node.get("objective", "No description"),
    )
    objective = f"{name}: {description}" if name else description
    level = node.get("level", node.get("depth", 0))
    node_report = node.get("node_report", "")
    auxiliary_info = node.get("auxiliary_info", {})
    info_count = (1 if node_report else 0) + (
        1 if auxiliary_info and len(auxiliary_info) > 0 else 0
    )
    status = node.get("status", "")
    children = node.get("decomposed", node.get("children", []))

    # Check if terminated/abandoned based on status or evaluation_details
    eval_details = node.get(
        "evaluation_details",
        node.get("last_evaluation", {}),
    )
    # Check new format first (current_status), then fall back to old format (task_done)
    current_status = (
        eval_details.get("current_status", "").lower()
        if eval_details.get("current_status")
        else ""
    )
    task_done = eval_details.get("task_done")
    is_terminated = status == "abandoned" or (
        current_status == "abandoned"
        or current_status == "terminated"
        or (isinstance(task_done, bool) and task_done is False)
    )
    is_completed = status == "done" or (
        current_status == "done"
        or current_status == "completed"
        or (isinstance(task_done, bool) and task_done is True)
    )

    # Tree structure symbols
    if indent == 0:
        connector = "🌲 "
    else:
        connector = "└── " if is_last else "├── "

    # Status indicators
    status = ""
    if is_terminated:
        status = f"{DIM}✂️ PRUNED{RESET} "
    elif is_completed:
        status = f"{GREEN}✓ DONE{RESET} "
    else:
        status = f"{YELLOW}⚙️ IN PROGRESS{RESET} "

    # Format objective (truncate if too long)
    max_len = 80 - len(prefix) - len(connector)
    if len(objective) > max_len:
        objective_display = objective[: max_len - 3] + "..."
    else:
        objective_display = objective

    # Print current node
    print(f"{prefix}{connector}{BOLD}{CYAN}[{node_id}]{RESET} {status}")
    print(
        f"{prefix}{'    ' if is_last else '│   '}{DIM}├─ Objective:{RESET} {objective_display}",
    )
    # Show status if available
    status_display = f" | {DIM}Status:{RESET} {status}" if status else ""
    print(
        f"{prefix}{'    ' if is_last else '│   '}{DIM}├─ Level:{RESET} {level} | "
        f"{DIM}Info Items:{RESET} {MAGENTA}{info_count}{RESET}{status_display}",
    )

    # Print evaluation if exists
    eval_details = node.get(
        "evaluation_details",
        node.get("last_evaluation", {}),
    )
    if eval_details:
        # Check if new format is present
        current_status = eval_details.get("current_status")
        if current_status is not None:
            # New format
            eval_status = (
                f"{GREEN}{current_status.upper()}{RESET}"
                if current_status.lower() in ["done", "completed"]
                else f"{DIM}{current_status.upper()}{RESET}"
            )
            current_task_summary = eval_details.get("current_task_summary", "")
            summary_preview = (
                current_task_summary[:50] + "..."
                if len(current_task_summary) > 50
                else current_task_summary
            )
            print(
                f"{prefix}{'    ' if is_last else '│   '}{DIM}└─ Eval:{RESET} {eval_status} - {summary_preview}",
            )
        else:
            # Old format (backward compatibility)
            reason_for_status = eval_details.get(
                "reason_for_status",
                eval_details.get("reasoning", "N/A"),
            )
            task_done = eval_details.get("task_done")
            if isinstance(task_done, bool):
                eval_status = (
                    f"{GREEN}DONE{RESET}"
                    if task_done
                    else f"{DIM}NOT DONE{RESET}"
                )
            else:
                eval_status = f"{YELLOW}UNKNOWN{RESET}"
            print(
                f"{prefix}{'    ' if is_last else '│   '}{DIM}└─ Eval:{RESET} {eval_status} - {reason_for_status[:50]}...",
            )

    # Print children
    if children:
        for i, child in enumerate(children):
            is_last_child = i == len(children) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_terminal_tree(child, indent + 1, is_last_child, new_prefix)


def generate_html_visualization(
    node: Dict[str, Any],
    stats: Dict[str, Any],
) -> str:
    """Generate an interactive HTML visualization with professional styling"""

    def node_to_html(n: Dict[str, Any], html_level: int = 0) -> str:
        """Convert node to HTML tree structure"""
        node_id = n.get("id", n.get("node_id", "unknown"))
        name = n.get("name", "")
        description = n.get(
            "description",
            n.get("objective", "No description"),
        )
        objective = f"{name}: {description}" if name else description
        level = n.get("level", n.get("depth", 0))
        node_report = n.get("node_report", "")
        auxiliary_info = n.get("auxiliary_info", {})
        info_count = (1 if node_report else 0) + (
            1 if auxiliary_info and len(auxiliary_info) > 0 else 0
        )
        status = n.get("status", "")
        children = n.get("decomposed", n.get("children", []))

        # Check if terminated/abandoned based on status or evaluation_details
        eval_details = n.get("evaluation_details", {})
        # Check new format first (current_status), then fall back to old format (task_done)
        current_status = (
            eval_details.get("current_status", "").lower()
            if eval_details.get("current_status")
            else ""
        )
        task_done = eval_details.get("task_done")
        is_terminated = status == "abandoned" or (
            current_status == "abandoned"
            or current_status == "terminated"
            or (isinstance(task_done, bool) and task_done is False)
        )
        is_completed = status == "done" or (
            current_status == "done"
            or current_status == "completed"
            or (isinstance(task_done, bool) and task_done is True)
        )

        # Determine node status class from status field or derived state
        if status == "abandoned" or is_terminated:
            status_class = "pruned"
            status_text = "✂️ Abandoned"
        elif status == "done" or is_completed:
            status_class = "completed"
            status_text = "✓ Completed"
        elif status == "in_progress":
            status_class = "running"
            status_text = "⚙️ In Progress"
        elif status == "todo":
            status_class = "running"
            status_text = "📋 Todo"
        else:
            status_class = "running"
            status_text = (
                f"⚙️ {status.capitalize()}" if status else "⚙️ Running"
            )

        html = f"""
        <div class="node {status_class}" style="margin-left: {html_level * 30}px;">
            <div class="node-header" onclick="toggleNode(this)">
                <span class="toggle-icon">−</span>
                <span class="node-id">[{node_id}]</span>
                <span class="status-badge status-{status_class}">{status_text}</span>
                <span class="node-objective">{objective}</span>
            </div>
            <div class="node-content">
                <div class="node-details">
                    <div class="node-stats">
                        <span class="stat"><strong>Level:</strong> {level}</span>
                        <span class="stat"><strong>Info Items:</strong> <span class="highlight">{info_count}</span></span>
                        {f'<span class="stat"><strong>Status:</strong> {status}</span>' if status else ''}
                    </div>
        """

        # Add evaluation details
        eval_details = n.get(
            "evaluation_details",
            n.get("last_evaluation", {}),
        )
        if eval_details:
            # Check if new format is present
            current_status = eval_details.get("current_status")
            current_task_summary = eval_details.get("current_task_summary")
            follow_up_subtasks = eval_details.get("follow_ups", [])
            remain_knowledge_gaps = eval_details.get(
                "remain_knowledge_gaps",
                "",
            )
            response = eval_details.get("response", "")

            if current_status is not None:
                # New format
                eval_result = current_status.upper()
                eval_class = (
                    "eval-continue"
                    if current_status.lower() in ["done", "completed"]
                    else "eval-terminate"
                )

                html += f"""
                    <div class="evaluation {eval_class}">
                        <strong>Status:</strong> {eval_result}<br>
                """

                if current_task_summary:
                    html += f"""
                        <br><strong>Task Summary:</strong><br>
                        <div class="eval-content">{current_task_summary}</div>
                    """

                if follow_up_subtasks:
                    html += """
                        <br><strong>Follow-up:</strong><ul class="eval-list">
                    """
                    for subtask in follow_up_subtasks:
                        # Escape HTML in subtask text
                        subtask_escaped = (
                            subtask.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        html += f"<li>{subtask_escaped}</li>"
                    html += "</ul>"

                if remain_knowledge_gaps:
                    # Convert markdown checkboxes to HTML and escape other content
                    gaps_html = (
                        remain_knowledge_gaps.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    gaps_html = gaps_html.replace("\n", "<br>")
                    html += f"""
                        <br><strong>Remaining Knowledge Gaps:</strong><br>
                        <div class="eval-content eval-knowledge-gaps">{gaps_html}</div>
                    """

                if response:
                    response_escaped = response.replace(
                        "</script>",
                        "<\\/script>",
                    )
                    html += f"""
                        <br><strong>Response:</strong><br>
                        <div class="eval-content eval-response markdown-content">
                            <script type="text/plain">{response_escaped}</script>
                        </div>
                    """

                html += "</div>"
            else:
                # Old format (backward compatibility)
                reason_for_status = eval_details.get(
                    "reason_for_status",
                    eval_details.get("reasoning", "N/A"),
                )
                task_done = eval_details.get("task_done")
                if isinstance(task_done, bool):
                    eval_result = "DONE" if task_done else "NOT DONE"
                    eval_class = (
                        "eval-continue" if task_done else "eval-terminate"
                    )
                else:
                    eval_result = "UNKNOWN"
                    eval_class = "eval-continue"
                progress_summary = eval_details.get("progress_summary", "")
                html += f"""
                    <div class="evaluation {eval_class}">
                        <strong>Evaluation:</strong> {eval_result}<br>
                        <em>{reason_for_status}</em>
                        {f'<br><br><strong>Progress:</strong><br><pre style="white-space: pre-wrap; font-size: 12px;">{progress_summary}</pre>' if progress_summary else ''}
                    </div>
                """

        # Add node report and auxiliary info
        if node_report or auxiliary_info:
            html += '<div class="info-items"><strong>Node Information:</strong><ul>'
            if node_report:
                preview = node_report
                html += f'<li><strong>[Report]</strong> <pre style="white-space: pre-wrap; font-size: 12px;">{preview}</pre></li>'
            if auxiliary_info:
                aux_info_str = (
                    json.dumps(auxiliary_info, indent=2)
                    if isinstance(auxiliary_info, dict)
                    else str(auxiliary_info)
                )
                preview = (
                    aux_info_str[:2000] + "..."
                    if len(aux_info_str) > 2000
                    else aux_info_str
                )
                html += f'<li><strong>[Metadata]</strong> <pre style="white-space: pre-wrap; font-size: 12px;">{preview}</pre></li>'
            html += "</ul></div>"

        html += "</div>"  # Close node-details

        # Add children
        if children:
            html += '<div class="children">'
            for child in children:
                html += node_to_html(child, html_level + 1)
            html += "</div>"

        html += "</div></div>"
        return html

    tree_html = node_to_html(node)

    # Check for root_full_report
    root_full_report_section = ""
    root_full_report = node.get("root_full_report", "")
    if root_full_report:
        report_escaped = root_full_report.replace("</script>", "<\\/script>")
        root_full_report_section = f"""
        <div class="root-full-report">
            <h1>📄 Full Research Report</h1>
            <div class="root-full-report-content markdown-content">
                <script type="text/plain">{report_escaped}</script>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Tree Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px 40px;
            border-bottom: 4px solid #f6d365;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
            margin-top: 8px;
        }}

        .stats-panel {{
            background: #f8f9fa;
            padding: 25px 40px;
            border-bottom: 1px solid #e0e0e0;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}

        .stat-card {{
            background: white;
            padding: 18px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            transition: transform 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        }}

        .stat-card .label {{
            font-size: 13px;
            color: #666;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stat-card .value {{
            font-size: 28px;
            font-weight: 700;
            color: #1e3c72;
            margin-top: 8px;
        }}

        .tree-container {{
            padding: 30px 40px;
            max-height: 800px;
            overflow-y: auto;
        }}

        .node {{
            margin: 15px 0;
            border-left: 1px solid #e0e0e0;
            padding-left: 15px;
            transition: all 0.3s;
        }}

        .node.completed {{
            border-left-color: #4caf50;
        }}

        .node.pruned {{
            border-left-color: #9e9e9e;
            opacity: 0.85;
        }}

        .node.running {{
            border-left-color: #ff9800;
        }}

        .node-header {{
            cursor: pointer;
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.2s;
            border: 1px solid #e0e0e0;
        }}

        .node-header:hover {{
            background: #e9ecef;
            border-color: #667eea;
        }}

        .node-id {{
            font-family: 'Courier New', monospace;
            font-weight: 700;
            color: #667eea;
            font-size: 14px;
        }}

        .status-badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .status-completed {{
            background: #d4edda;
            color: #155724;
        }}

        .status-pruned {{
            background: #e0e0e0;
            color: #616161;
        }}

        .status-running {{
            background: #fff3cd;
            color: #856404;
        }}

        .node-objective {{
            flex: 1;
            font-size: 15px;
            font-weight: 500;
            color: #333;
        }}

        .toggle-icon {{
            font-size: 16px;
            font-weight: bold;
            color: #667eea;
            width: 20px;
            text-align: center;
            flex-shrink: 0;
            user-select: none;
        }}

        .node-content {{
            margin-top: 12px;
        }}

        .node-header.collapsed + .node-content {{
            display: none;
        }}

        .node-details {{
            padding: 16px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}

        .node-stats {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}

        .stat {{
            font-size: 14px;
            color: #555;
        }}

        .stat .highlight {{
            color: #667eea;
            font-weight: 700;
        }}

        .evaluation {{
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 14px;
        }}

        .eval-continue {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            color: #155724;
        }}

        .eval-terminate {{
            background: #f5f5f5;
            border-left: 4px solid #9e9e9e;
            color: #616161;
        }}

        .eval-content {{
            margin-top: 8px;
            padding: 8px;
            background: rgba(255, 255, 255, 0.5);
            border-radius: 4px;
            line-height: 1.6;
            font-size: 13px;
        }}

        .eval-list {{
            margin-top: 8px;
            margin-left: 20px;
            padding-left: 0;
        }}

        .eval-list li {{
            margin: 6px 0;
            line-height: 1.5;
        }}

        .eval-knowledge-gaps {{
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            font-size: 12px;
        }}

        .eval-response {{
            max-height: 400px;
            overflow-y: auto;
            padding: 12px;
        }}

        .markdown-content h1 {{
            font-size: 18px;
            margin-top: 15px;
            margin-bottom: 10px;
            color: #1e3c72;
            border-bottom: 2px solid #667eea;
            padding-bottom: 5px;
        }}

        .markdown-content h2 {{
            font-size: 16px;
            margin-top: 12px;
            margin-bottom: 8px;
            color: #2a5298;
        }}

        .markdown-content h3 {{
            font-size: 14px;
            margin-top: 10px;
            margin-bottom: 6px;
            color: #3d6bb3;
        }}

        .markdown-content ul, .markdown-content ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}

        .markdown-content li {{
            margin: 4px 0;
            line-height: 1.5;
        }}

        .markdown-content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}

        .markdown-content th, .markdown-content td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}

        .markdown-content th {{
            background: #f2f2f2;
            font-weight: 600;
            color: #1e3c72;
        }}

        .markdown-content hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 20px 0;
        }}

        .markdown-content code {{
            background: #f5f5f5;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}

        .markdown-content pre {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }}

        .markdown-content blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 15px;
            margin: 10px 0;
            color: #666;
        }}

        .root-full-report {{
            background: #f8f9fa;
            padding: 30px 40px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .root-full-report h1 {{
            font-size: 24px;
            color: #1e3c72;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .root-full-report-content {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            line-height: 1.8;
            font-size: 14px;
            color: #333;
        }}

        .info-items {{
            font-size: 13px;
            color: #555;
        }}

        .info-items ul {{
            margin-top: 8px;
            margin-left: 20px;
        }}

        .info-items li {{
            margin: 6px 0;
            line-height: 1.6;
        }}

        .children {{
            margin-top: 10px;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            font-size: 13px;
            border-top: 1px solid #e0e0e0;
        }}

        ::-webkit-scrollbar {{
            width: 10px;
        }}

        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
        }}

        ::-webkit-scrollbar-thumb {{
            background: #888;
            border-radius: 5px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: #555;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌲 Research Tree Visualization</h1>
            <div class="subtitle">Tree-based Deep Research Agent Exploration Process</div>
        </div>

        <div class="stats-panel">
            <div class="stat-card">
                <div class="label">Total Nodes</div>
                <div class="value">{stats['total_nodes']}</div>
            </div>
            <div class="stat-card">
                <div class="label">Max Level</div>
                <div class="value">{stats['max_depth']}</div>
            </div>
            <div class="stat-card">
                <div class="label">Info Items</div>
                <div class="value">{stats['total_info_items']}</div>
            </div>
            <div class="stat-card">
                <div class="label">Completed</div>
                <div class="value">{stats['completed_nodes']}/{stats['total_nodes']}</div>
            </div>
            <div class="stat-card">
                <div class="label">Pruned</div>
                <div class="value">{stats['terminated_nodes']}</div>
            </div>
        </div>

        {root_full_report_section}

        <div class="tree-container">
            {tree_html}
        </div>

        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Alias Tree Deep Research Agent
        </div>
    </div>

    <script>
        function toggleNode(header) {{
            header.classList.toggle('collapsed');
            const icon = header.querySelector('.toggle-icon');
            if (header.classList.contains('collapsed')) {{
                icon.textContent = '+';
            }} else {{
                icon.textContent = '−';
            }}
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            // Render all markdown content
            document.querySelectorAll('.markdown-content').forEach(element => {{
                const script = element.querySelector('script[type="text/plain"]');
                if (script) {{
                    element.innerHTML = marked.parse(script.textContent);
                }}
            }});
        }});
    </script>
</body>
</html>"""

    # with open(output_path, "w", encoding="utf-8") as f:
    #     f.write(html_content)
    return html_content


def generate_summary_report(
    node: Dict[str, Any],
    stats: Dict[str, Any],
) -> str:
    """Generate a text summary report"""
    lines = []
    lines.append("=" * 80)
    lines.append("RESEARCH TREE ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append("")

    root_name = node.get("name", "")
    root_description = node.get("description", node.get("objective", "N/A"))
    root_objective = (
        f"{root_name}: {root_description}" if root_name else root_description
    )
    lines.append(f"Root Objective: {root_objective}")
    lines.append("")

    lines.append("STATISTICS:")
    lines.append(f"  • Total Nodes: {stats['total_nodes']}")
    lines.append(f"  • Maximum Depth: {stats['max_depth']}")
    lines.append(f"  • Total Information Items: {stats['total_info_items']}")
    lines.append(
        f"  • Completed Nodes: {stats['completed_nodes']}/{stats['total_nodes']}",
    )
    lines.append(f"  • Pruned Nodes: {stats['terminated_nodes']}")
    if stats["total_nodes"] > 0:
        lines.append(
            f"  • Average Info/Node: {stats['total_info_items']/stats['total_nodes']:.2f}",
        )
    lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Visualize research tree from JSON file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualize_research_tree.py logs/research_tree_20231023_120000.json
  python visualize_research_tree.py logs/research_tree_latest.json --output visualization.html
  python visualize_research_tree.py logs/research_tree_latest.json --no-html
        """,
    )

    parser.add_argument("input_file", help="Path to research tree JSON file")
    parser.add_argument(
        "--output",
        "-o",
        help="Output HTML file path (default: auto-generated)",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip HTML generation, only show terminal view",
    )
    parser.add_argument(
        "--no-terminal",
        action="store_true",
        help="Skip terminal view, only generate HTML",
    )

    args = parser.parse_args()

    # Load tree data
    try:
        tree_data = load_tree_json(args.input_file)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.input_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON file: {e}")
        return 1

    # Calculate statistics
    stats = calculate_tree_stats(tree_data)

    # Print terminal view
    if not args.no_terminal:
        print("\n" + "=" * 80)
        print("RESEARCH TREE VISUALIZATION")
        print("=" * 80)
        print()
        print(generate_summary_report(tree_data, stats))
        print()
        print_terminal_tree(tree_data)
        print("\n" + "=" * 80)

    # Generate HTML visualization
    if not args.no_html:
        if args.output:
            output_path = args.output
        else:
            input_path = Path(args.input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                input_path.parent / f"research_tree_viz_{timestamp}.html"
            )

        html_content = generate_html_visualization(tree_data, stats)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n✅ HTML visualization generated: {output_path}")
        print(f"   Open in browser: file://{Path(output_path).absolute()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
