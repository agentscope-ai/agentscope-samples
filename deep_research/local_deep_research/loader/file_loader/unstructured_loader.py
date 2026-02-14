import os
import shutil
from typing import List

from langchain_core.documents import Document

from local_deep_research.loader.file_loader.base import BaseLoader
from local_deep_research.utils import log


class UnstructuredLoader(BaseLoader):
    """
    Loader for unstructured documents using the unstructured-io library.

    This loader processes various document formats using the unstructured-io library's
    processing pipeline, extracting text and metadata from complex document formats.
    """

    def __init__(self):
        """
        Initialize the UnstructuredLoader.

        Creates a temporary directory for processed outputs and cleans up any existing ones.
        """
        self.directory_with_results = "./pdf_processed_outputs"
        if os.path.exists(self.directory_with_results):
            shutil.rmtree(self.directory_with_results)
        os.makedirs(self.directory_with_results)

    def load_pipeline(self, input_path: str) -> List[Document]:
        """
        Process documents using the unstructured-io pipeline.

        Args:
            input_path: Path to the file or directory to be processed.

        Returns:
            A list of Document objects extracted from the processed files.

        Note:
            If UNSTRUCTURED_API_KEY and UNSTRUCTURED_API_URL environment variables are set,
            the API-based partitioning will be used. Otherwise, local partitioning will be used.
        """
        from unstructured_ingest.interfaces import ProcessorConfig
        from unstructured_ingest.pipeline.pipeline import Pipeline
        from unstructured_ingest.processes.connectors.local import (
            LocalConnectionConfig,
            LocalDownloaderConfig,
            LocalIndexerConfig,
            LocalUploaderConfig,
        )
        from unstructured_ingest.processes.partitioner import PartitionerConfig

        # Check if API environment variables are set
        api_key = os.getenv("UNSTRUCTURED_API_KEY")
        api_url = os.getenv("UNSTRUCTURED_API_URL")
        use_api = api_key is not None and api_url is not None

        if use_api:
            log.color_print("Using Unstructured API for document processing")
        else:
            log.color_print(
                "Using local processing for documents (UNSTRUCTURED_API_KEY or UNSTRUCTURED_API_URL not set)"
            )

        Pipeline.from_configs(
            context=ProcessorConfig(),
            indexer_config=LocalIndexerConfig(input_path=input_path),
            downloader_config=LocalDownloaderConfig(),
            source_connection_config=LocalConnectionConfig(),
            partitioner_config=PartitionerConfig(
                partition_by_api=use_api,
                api_key=api_key,
                partition_endpoint=api_url,
                strategy="hi_res",
            ),
            uploader_config=LocalUploaderConfig(output_dir=self.directory_with_results),
        ).run()

        from unstructured.staging.base import elements_from_json

        elements = []
        for filename in os.listdir(self.directory_with_results):
            if filename.endswith(".json"):
                file_path = os.path.join(self.directory_with_results, filename)
                try:
                    elements.extend(elements_from_json(filename=file_path))
                except IOError:
                    log.color_print(f"Error: Could not read file {filename}.")

        documents = []
        for element in elements:
            metadata = element.metadata.to_dict()
            metadata["reference"] = input_path  # TODO test it
            documents.append(
                Document(
                    page_content=element.text,
                    metadata=metadata,
                )
            )
        return documents

    def load_file(self, file_path: str) -> List[Document]:
        """
        Load a single file using the unstructured-io pipeline.

        Args:
            file_path: Path to the file to be processed.

        Returns:
            A list of Document objects extracted from the processed file.
        """
        return self.load_pipeline(file_path)

    def load_directory(self, directory: str) -> List[Document]:
        """
        Load all supported files from a directory using the unstructured-io pipeline.

        Args:
            directory: Path to the directory containing files to be processed.

        Returns:
            A list of Document objects extracted from all processed files.
        """
        return self.load_pipeline(directory)

    @property
    def supported_file_types(self) -> List[str]:
        """
        Get the list of file extensions supported by the unstructured-io library. Please refer to the Unstructured documentation for more details: https://docs.unstructured.io/ui/supported-file-types.

        Returns:
            A comprehensive list of supported file extensions.

        Note:
            The unstructured-io library supports a wide range of document formats
            including office documents, images, emails, and more.
        """
        return [
            "abw",
            "bmp",
            "csv",
            "cwk",
            "dbf",
            "dif",
            "doc",
            "docm",
            "docx",
            "dot",
            "dotm",
            "eml",
            "epub",
            "et",
            "eth",
            "fods",
            "gif",
            "heic",
            "htm",
            "html",
            "hwp",
            "jpeg",
            "jpg",
            "md",
            "mcw",
            "mw",
            "odt",
            "org",
            "p7s",
            "pages",
            "pbd",
            "pdf",
            "png",
            "pot",
            "potm",
            "ppt",
            "pptm",
            "pptx",
            "prn",
            "rst",
            "rtf",
            "sdp",
            "sgl",
            "svg",
            "sxg",
            "tiff",
            "txt",
            "tsv",
            "uof",
            "uos1",
            "uos2",
            "web",
            "webp",
            "wk2",
            "xls",
            "xlsb",
            "xlsm",
            "xlsx",
            "xlw",
            "xml",
            "zabw",
        ]
