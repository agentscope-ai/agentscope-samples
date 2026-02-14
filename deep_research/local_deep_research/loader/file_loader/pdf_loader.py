from typing import List

from langchain_core.documents import Document

from local_deep_research.loader.file_loader.base import BaseLoader


class PDFLoader(BaseLoader):
    """
    Loader for PDF files.

    This loader handles PDF files and also supports text files with extensions like .txt and .md,
    converting them into Document objects for further processing.
    """

    def __init__(self):
        """
        Initialize the PDFLoader.
        """
        pass

    def load_file(self, file_path: str) -> List[Document]:
        """
        Load a PDF file and convert it to a Document object.

        Args:
            file_path: Path to the PDF file to be loaded.

        Returns:
            A list containing a single Document object with the file content and reference.

        Note:
            This loader also supports .txt and .md files for convenience.
        """
        import pdfplumber

        if file_path.endswith(".pdf"):
            with pdfplumber.open(file_path) as file:
                page_content = "\n\n".join([page.extract_text() for page in file.pages])
                return [Document(page_content=page_content, metadata={"reference": file_path})]
        elif file_path.endswith(".txt") or file_path.endswith(".md"):
            with open(file_path, "r", encoding="utf-8") as file:
                page_content = file.read()
                return [Document(page_content=page_content, metadata={"reference": file_path})]

    @property
    def supported_file_types(self) -> List[str]:
        """
        Get the list of file extensions supported by this loader.

        Returns:
            A list of supported file extensions: ["pdf", "md", "txt"].
        """
        return ["pdf", "md", "txt"]
