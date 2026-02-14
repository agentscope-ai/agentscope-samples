import os
from typing import List

from langchain_core.documents import Document

from local_deep_research.loader.file_loader.base import BaseLoader
from local_deep_research.utils import log

class DoclingLoader(BaseLoader):
    """
    Loader that utilizes Docling's DocumentConverter and HierarchicalChunker
    to convert and chunk files (e.g. Markdown or HTML) into Document objects.
    """

    def __init__(self):
        """
        Initialize the DoclingLoader with DocumentConverter and HierarchicalChunker instances.
        """
        from docling.document_converter import DocumentConverter
        from docling_core.transforms.chunker import HierarchicalChunker

        self.converter = DocumentConverter()
        self.chunker = HierarchicalChunker()

    def load_file(self, file_path: str) -> List[Document]:
        """
        Load a local file (or URL) using docling's conversion and perform hierarchical chunking.

        Args:
            file_path: Path or URL of the file to be loaded.

        Returns:
            A list of Document objects, each representing a chunk.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file type is not supported.
            IOError: If there is an error reading the file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Error: File '{file_path}' does not exist.")

        # Check if the file has a supported extension
        file_extension = os.path.splitext(file_path)[1].lower().lstrip(".")
        if file_extension not in self.supported_file_types:
            supported_formats = ", ".join(self.supported_file_types)
            raise ValueError(
                f"Unsupported file type: '{file_extension}'. "
                f"Supported file types are: {supported_formats}"
            )

        try:
            conversion_result = self.converter.convert(file_path)
            docling_document = conversion_result.document

            chunks = list(self.chunker.chunk(docling_document))

            documents = []
            for chunk in chunks:
                metadata = {"reference": file_path, "text": chunk.text}
                documents.append(Document(page_content=chunk.text, metadata=metadata))
            return documents
        except Exception as e:
            log.color_print(f"Error processing file {file_path}: {str(e)}")
            raise IOError(f"Failed to process file {file_path}: {str(e)}")

    def load_directory(self, directory: str) -> List[Document]:
        """
        Load all supported files from a directory.

        Args:
            directory: Path to the directory containing files to be loaded.

        Returns:
            A list of Document objects from all supported files in the directory.

        Raises:
            NotADirectoryError: If the specified path is not a directory.
        """
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Error: '{directory}' is not a directory.")

        return super().load_directory(directory)

    @property
    def supported_file_types(self) -> List[str]:
        """
        Return the list of file extensions supported by this loader.

        Supported formats (refer to the official website: https://docling-project.github.io/docling/usage/supported_formats/):
        - PDF
        - Office formats: DOCX, XLSX, PPTX
        - Markdown
        - AsciiDoc
        - HTML, XHTML
        - CSV
        - Images: PNG, JPEG, TIFF, BMP
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
