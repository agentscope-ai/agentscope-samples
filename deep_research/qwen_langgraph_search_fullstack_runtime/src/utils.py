# -*- coding: utf-8 -*-
import time
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage


def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


def format_time(timestamp_param: str, format_str: str = "%Y-%m-%d") -> str:
    if not timestamp_param or not timestamp_param.isnumeric():
        return ""

    try:
        timestamp = int(timestamp_param)
        return time.strftime(format_str, time.localtime(timestamp))
    except (ValueError, OverflowError, OSError):
        return ""


def get_research_topic(messages: List[AnyMessage]) -> str:
    """
    Get the research topic from the messages.
    """
    # check if request has a history and combine the messages
    # into a single string
    if len(messages) == 1:
        research_topic = messages[-1].content
    else:
        research_topic = ""
        for message in messages:
            if isinstance(message, HumanMessage):
                research_topic += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                research_topic += f"Assistant: {message.content}\n"
    return research_topic


def insert_citation_markers(text, citations_list):
    """
    Inserts citation markers into a text string based on start and end indices.

    Args:
        text (str): The original text string.
        citations_list (list): A list of dictionaries, where each dictionary
                               contains 'start_index', 'end_index', and
                               'segment_string' (the marker to insert).
                               Indices are assumed to be for the original text.

    Returns:
        str: The text with citation markers inserted.
    """
    # Sort citations by end_index in descending order.
    # If end_index is the same, secondary sort by start_index descending.
    # This ensures that insertions at the end of the string don't affect
    # the indices of earlier parts of the string that still
    # need to be processed.
    sorted_citations = sorted(
        citations_list,
        key=lambda c: (c["end_index"], c["start_index"]),
        reverse=True,
    )

    modified_text = text
    for citation_info in sorted_citations:
        # These indices refer to positions in the *original* text,
        # but since we iterate from the end, they remain valid for insertion
        # relative to the parts of the string already processed.
        end_idx = citation_info["end_index"]
        marker_to_insert = ""
        for segment in citation_info["segments"]:
            marker_to_insert += (
                f" [{segment['label']}]({segment['short_url']})"
            )
        # Insert the citation marker at the original end_idx position
        modified_text = (
            modified_text[:end_idx]
            + marker_to_insert
            + modified_text[end_idx:]
        )

    return modified_text


def custom_resolve_urls(
    search_results: List[Dict[str, Any]],
    uid: str,
) -> Dict[str, str]:
    prefix = "https://search-result.local/id/"
    resolved_map = {}

    for idx, result in enumerate(search_results):
        url = result.get("url", "")
        if url and url not in resolved_map:
            resolved_map[url] = f"{prefix}{uid}-{idx}"

    return resolved_map


def custom_get_citations(
    search_results: List[Dict[str, Any]],
    resolved_urls_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    citations = []

    for idx, result in enumerate(search_results):
        url = result.get("url", "")
        title = result.get("title", f"搜索结果 {idx + 1}")

        if url:
            citation = {
                "start_index": 0,  # 简化处理，实际应用中可以更精确
                "end_index": len(title),
                "segments": [
                    {
                        "label": title[:50] + "..."
                        if len(title) > 50
                        else title,
                        "short_url": resolved_urls_map.get(url, url),
                        "value": url,
                    },
                ],
            }
            citations.append(citation)

    return citations
