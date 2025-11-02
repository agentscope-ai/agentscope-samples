import os
from typing import List, Optional

from firecrawl import Firecrawl
from firecrawl.v2.types import Document as FirecrawlDocument, ScrapeOptions
from langchain_core.documents import Document

from local_deep_research.loader.web_crawler.base import BaseCrawler


class FireCrawlCrawler(BaseCrawler):
    """
    Web crawler using the FireCrawl service.

    This crawler uses the FireCrawl service to crawl web pages and convert them
    into markdown format for further processing. It supports both single-page scraping
    and recursive crawling of multiple pages.
    """

    def __init__(self, **kwargs):
        """
        Initialize the FireCrawlCrawler.

        Args:
            **kwargs: Optional keyword arguments.
        """
        super().__init__(**kwargs)
        self.client: Firecrawl | None = None

    def crawl_url(
        self,
        url: str,
        max_depth: Optional[int] = None,
        limit: Optional[int] = None,
        allow_backward_links: Optional[bool] = None,
    ) -> List[Document]:
        """
        Dynamically crawls a URL using either scrape_url or crawl_url:

        - Uses scrape_url for single-page extraction if no params are provided.
        - Uses crawl_url to recursively gather pages when any param is provided.

        Args:
            url (str): The starting URL to crawl.
            max_depth (Optional[int]): Maximum depth for recursive crawling (default: 2).
            limit (Optional[int]): Maximum number of pages to crawl (default: 20).
            allow_backward_links (Optional[bool]): Allow crawling pages outside the URL's children (default: False).

        Returns:
            List[Document]: List of Document objects with page content and metadata.
        """
        # Lazy init of Firecrawl v2 client
        if self.client is None:
            self.client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

        # if user just inputs a single url as param
        # scrape single page
        if max_depth is None and limit is None and allow_backward_links is None:
            # Call the new Firecrawl API, passing formats directly
            scrape_doc = self.client.scrape(url=url, formats=["markdown"])
            data = scrape_doc.model_dump()
            return [
                Document(
                    page_content=data.get("markdown", ""),
                    metadata={"reference": url, **data.get("metadata", {})},
                )
            ]

        # else, crawl multiple pages based on users' input params
        # set default values if not provided
        crawl_job = self.client.crawl(
            url=url,
            limit=limit or 20,
            max_discovery_depth=max_depth or 2,
            allow_external_links=bool(allow_backward_links),
            scrape_options=ScrapeOptions(formats=["markdown"]),
            poll_interval=5,
        )
        items: List[FirecrawlDocument] = crawl_job.data or []

        documents: List[Document] = []
        for item in items:
            item_dict = item.model_dump()
            md = item_dict.get("markdown", "")
            meta = item_dict.get("metadata", {}) or {}
            meta["reference"] = meta.get("url", url)
            documents.append(Document(page_content=md, metadata=meta))

        return documents
