import os
from typing import List

import requests
from langchain_core.documents import Document

from local_deep_research.loader.web_crawler.base import BaseCrawler


class JinaCrawler(BaseCrawler):
    """
    Web crawler using Jina AI's rendering service.

    This crawler uses Jina AI's rendering service to crawl web pages and convert them
    into markdown format for further processing.
    """

    def __init__(self, **kwargs):
        """
        Initialize the JinaCrawler.

        Args:
            **kwargs: Optional keyword arguments.

        Raises:
            ValueError: If the JINA_API_TOKEN environment variable is not set.
        """
        super().__init__(**kwargs)
        self.jina_api_token = os.getenv("JINA_API_TOKEN") or os.getenv("JINAAI_API_KEY")
        if not self.jina_api_token:
            raise ValueError("Missing JINA_API_TOKEN environment variable")

    def crawl_url(self, url: str) -> List[Document]:
        """
        Crawl a single URL using Jina AI's rendering service.

        Args:
            url: The URL to crawl.

        Returns:
            A list containing a single Document object with the markdown content and metadata.

        Raises:
            HTTPError: If the request to Jina AI's service fails.
        """
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "Authorization": f"Bearer {self.jina_api_token}",
            "X-Return-Format": "markdown",
        }

        response = requests.get(jina_url, headers=headers)
        response.raise_for_status()

        markdown_content = response.text
        metadata = {
            "reference": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }

        return [Document(page_content=markdown_content, metadata=metadata)]
