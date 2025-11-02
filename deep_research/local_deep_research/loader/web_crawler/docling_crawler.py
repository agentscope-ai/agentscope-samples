from typing import List

from langchain_core.documents import Document

from local_deep_research.loader.web_crawler.base import BaseCrawler
from local_deep_research.utils import log


class DoclingCrawler(BaseCrawler):
    """
    Web crawler using Docling's DocumentConverter and HierarchicalChunker.

    This crawler leverages Docling's capabilities to convert web pages into structured
    documents and chunk them appropriately for further processing.
    """

    def __init__(self, **kwargs):
        """
        Initialize the DoclingCrawler with DocumentConverter and HierarchicalChunker instances.

        Args:
            **kwargs: Optional keyword arguments.
        """
        super().__init__(**kwargs)
        from docling.document_converter import DocumentConverter
        from docling_core.transforms.chunker import HierarchicalChunker

        self.converter = DocumentConverter()
        self.chunker = HierarchicalChunker()

    def crawl_url(self, url: str, **crawl_kwargs) -> List[Document]:
        """
        Crawl a single URL using Docling's conversion and perform hierarchical chunking.

        Args:
            url: The URL to crawl.
            **crawl_kwargs: Optional keyword arguments for the crawling process.

        Returns:
            A list of Document objects, each representing a chunk from the crawled URL.

        Raises:
            IOError: If there is an error processing the URL.
        """
        try:
            # Use Docling to convert the URL to a document
            conversion_result = self.converter.convert(url)
            docling_document = conversion_result.document

            # Chunk the document using hierarchical chunking
            chunks = list(self.chunker.chunk(docling_document))

            documents = []
            for chunk in chunks:
                metadata = {"reference": url, "text": chunk.text}
                documents.append(Document(page_content=chunk.text, metadata=metadata))

            return documents

        except Exception as e:
            log.color_print(f"Error processing URL {url}: {str(e)}")
            raise IOError(f"Failed to process URL {url}: {str(e)}")

    @property
    def supported_file_types(self) -> List[str]:
        """
        Return the list of file types and formats supported by Docling.

        Supported formats (refer to the official Docling documentation: https://docling-project.github.io/docling/usage/supported_formats/):
        - PDF
        - Office formats: DOCX, XLSX, PPTX
        - Markdown
        - AsciiDoc
        - HTML, XHTML
        - CSV
        - Images: PNG, JPEG, TIFF, BMP

        Returns:
            A list of file extensions supported by this crawler.
        """
        return [
            "pdf",
            "docx",
            "xlsx",
            "pptx",
            "md",
            "adoc",
            "asciidoc",
            "html",
            "xhtml",
            "csv",
            "png",
            "jpg",
            "jpeg",
            "tif",
            "tiff",
            "bmp",
        ]
