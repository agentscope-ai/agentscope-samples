import asyncio
from typing import List

from langchain_core.documents import Document

from local_deep_research.loader.web_crawler.base import BaseCrawler
from local_deep_research.utils import log


class Crawl4AICrawler(BaseCrawler):
    """
    Web crawler using the Crawl4AI library.

    This crawler uses the Crawl4AI library to crawl web pages asynchronously and convert them
    into markdown format for further processing. It supports both single-page crawling
    and batch crawling of multiple pages.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Crawl4AICrawler.

        Args:
            **kwargs: Optional keyword arguments.
                browser_config: Configuration for the browser used by Crawl4AI.
        """
        super().__init__(**kwargs)
        self.crawler = None  # Lazy init
        self.browser_config = kwargs.get("browser_config", None)

    def _lazy_init(self):
        """
        Initialize the crawler lazily when needed.

        This method creates the AsyncWebCrawler instance with the provided browser configuration
        only when it's first needed, to avoid unnecessary initialization.
        """
        from crawl4ai import AsyncWebCrawler, BrowserConfig

        if self.crawler is None:
            config = BrowserConfig.from_kwargs(self.browser_config) if self.browser_config else None
            self.crawler = AsyncWebCrawler(config=config)

    async def _async_crawl(self, url: str) -> Document:
        """
        Asynchronously crawl a single URL.

        Args:
            url: The URL to crawl.

        Returns:
            A Document object with the markdown content and metadata from the URL.
        """
        if self.crawler is None:
            self._lazy_init()

        async with self.crawler as crawler:
            result = await crawler.arun(url)

            markdown_content = result.markdown or ""

            metadata = {
                "reference": url,
                "success": result.success,
                "status_code": result.status_code,
                "media": result.media,
                "links": result.links,
            }

            if hasattr(result, "metadata") and result.metadata:
                metadata["title"] = result.metadata.get("title", "")
                metadata["author"] = result.metadata.get("author", "")

            return Document(page_content=markdown_content, metadata=metadata)

    def crawl_url(self, url: str) -> List[Document]:
        """
        Crawl a single URL.

        Args:
            url: The URL to crawl.

        Returns:
            A list containing a single Document object with the markdown content and metadata,
            or an empty list if an error occurs.
        """
        try:
            document = asyncio.run(self._async_crawl(url))
            return [document]
        except Exception as e:
            log.error(f"Error during crawling {url}: {e}")
            return []

    async def _async_crawl_many(self, urls: List[str]) -> List[Document]:
        """
        Asynchronously crawl multiple URLs.

        Args:
            urls: A list of URLs to crawl.

        Returns:
            A list of Document objects with the markdown content and metadata from all URLs.
        """
        if self.crawler is None:
            self._lazy_init()
        async with self.crawler as crawler:
            results = await crawler.arun_many(urls)
            documents = []
            for result in results:
                markdown_content = result.markdown or ""
                metadata = {
                    "reference": result.url,
                    "success": result.success,
                    "status_code": result.status_code,
                    "media": result.media,
                    "links": result.links,
                }
                if hasattr(result, "metadata") and result.metadata:
                    metadata["title"] = result.metadata.get("title", "")
                    metadata["author"] = result.metadata.get("author", "")
                documents.append(Document(page_content=markdown_content, metadata=metadata))
            return documents

    def crawl_urls(self, urls: List[str], **crawl_kwargs) -> List[Document]:
        """
        Crawl multiple URLs.

        Args:
            urls: A list of URLs to crawl.
            **crawl_kwargs: Optional keyword arguments for the crawling process.

        Returns:
            A list of Document objects with the markdown content and metadata from all URLs,
            or an empty list if an error occurs.
        """
        try:
            return asyncio.run(self._async_crawl_many(urls))
        except Exception as e:
            log.error(f"Error during crawling {urls}: {e}")
            return []
