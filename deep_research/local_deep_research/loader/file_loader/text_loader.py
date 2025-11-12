from typing import List

from langchain_core.documents import Document

from local_deep_research.loader.file_loader.base import BaseLoader


class TextLoader(BaseLoader):
    """
    Loader for plain text files.

    This loader handles text files with extensions like .txt and .md,
    converting them into Document objects for further processing.
    """

    def __init__(self):
        """
        Initialize the TextLoader.
        """
        pass

    def load_file(self, file_path: str) -> List[Document]:
        """
        Load a text file and convert it to a Document object.

        Args:
            file_path: Path to the text file to be loaded.

        Returns:
            A list containing a single Document object with the file content and reference.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return [Document(page_content=f.read(), metadata={"reference": file_path})]

    @property
    def supported_file_types(self) -> List[str]:
        """
        Get the list of file extensions supported by this loader.

        Returns:
            A list of supported file extensions: ["txt", "md"].
        """
        return ["txt", "md"]
