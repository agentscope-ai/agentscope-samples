from abc import ABC
from typing import List

from langchain_core.documents import Document


class BaseCrawler(ABC):
    """
    Abstract base class for web crawlers.

    This class defines the interface for crawling web pages and converting them
    into Document objects for further processing.
    """

    def __init__(self, **kwargs):
        """
        Initialize the crawler with optional keyword arguments.

        Args:
            **kwargs: Optional keyword arguments for specific crawler implementations.
        """
        pass

    def crawl_url(self, url: str, **crawl_kwargs) -> List[Document]:
        """
        Crawl a single URL and convert it to Document objects.

        Args:
            url: The URL to crawl.
            **crawl_kwargs: Optional keyword arguments for the crawling process.

        Returns:
            A list of Document objects containing the content and metadata from the URL.

        Note:
            Implementations should include the URL reference in the metadata.
            e.g. return [Document(page_content=..., metadata={"reference": "www.abc.com/page1.html"})]
        """
        pass

    def crawl_urls(self, urls: List[str], **crawl_kwargs) -> List[Document]:
        """
        Crawl multiple URLs and return a list of Document objects.

        Args:
            urls: A list of URLs to crawl.
            **crawl_kwargs: Optional keyword arguments for the crawling process.

        Returns:
            A list of Document objects containing the content and metadata from all URLs.
        """
        documents = []
        for url in urls:
            documents.extend(self.crawl_url(url, **crawl_kwargs))
        return documents
