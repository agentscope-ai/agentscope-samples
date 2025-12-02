# -*- coding: utf-8 -*-
"""The agentic usage example for RAG in AgentScope, where the agent is
equipped with RAG tools to answer questions based on a knowledge base.

The example is more challenging for the agent, requiring the agent to
adjust the retrieval parameters to get relevant results.
"""
import asyncio
import hashlib
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from agentscope.embedding import DashScopeTextEmbedding
from agentscope.message import TextBlock
from agentscope.rag import Document, SimpleKnowledge, QdrantStore, TextReader
from agentscope.rag._document import DocMetadata

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

# Qdrant storage directory (relative to script location)
QDRANT_STORAGE_DIR = SCRIPT_DIR / "qdrant_storage"
QDRANT_CONTAINER_NAME = "qdrant"
QDRANT_HOST = "127.0.0.1"
QDRANT_PORT = 6333


def check_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_container_exists(container_name: str) -> bool:
    """Check if Docker container exists."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout
    except subprocess.CalledProcessError:
        return False


def check_container_running(container_name: str) -> bool:
    """Check if Docker container is running."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout
    except subprocess.CalledProcessError:
        return False


def start_qdrant_container() -> None:
    """Start Qdrant Docker container with specified storage location."""
    if not check_docker_available():
        raise RuntimeError(
            "Docker is not available. Please install Docker first.",
        )

    # Create storage directory if it doesn't exist
    QDRANT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    container_exists = check_container_exists(QDRANT_CONTAINER_NAME)
    container_running = check_container_running(QDRANT_CONTAINER_NAME)

    if container_running:
        # Verify the storage path is correct
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    QDRANT_CONTAINER_NAME,
                    "--format",
                    "{{range .Mounts}}{{.Source}}{{end}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            current_storage = result.stdout.strip()
            expected_storage = str(QDRANT_STORAGE_DIR.resolve())
            if current_storage == expected_storage:
                print(
                    f"Qdrant container '{QDRANT_CONTAINER_NAME}' is "
                    "already running with correct storage path.",
                )
                return
            else:
                print(
                    "Container exists but storage "
                    "path is different. Recreating...",
                )
                print(f"  Current: {current_storage}")
                print(f"  Expected: {expected_storage}")
                subprocess.run(
                    ["docker", "stop", QDRANT_CONTAINER_NAME],
                    check=False,
                )
                subprocess.run(
                    ["docker", "rm", QDRANT_CONTAINER_NAME],
                    check=False,
                )
                container_exists = False
        except subprocess.CalledProcessError:
            # If inspection fails, try to start it anyway
            pass

    if container_exists and not container_running:
        print(
            f"Starting existing Qdrant "
            f"container '{QDRANT_CONTAINER_NAME}'...",
        )
        subprocess.run(
            ["docker", "start", QDRANT_CONTAINER_NAME],
            check=True,
        )
    else:
        print(
            f"Creating and starting Qdrant "
            f"container '{QDRANT_CONTAINER_NAME}'...",
        )
        print(f"Storage location: {QDRANT_STORAGE_DIR}")
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                QDRANT_CONTAINER_NAME,
                "-p",
                f"{QDRANT_PORT}:6333",
                "-p",
                "6334:6334",
                "-v",
                f"{QDRANT_STORAGE_DIR.resolve()}:/qdrant/storage",
                "qdrant/qdrant:latest",
            ],
            check=True,
        )

    # Wait for Qdrant to be ready
    print("Waiting for Qdrant to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            import urllib.request

            with urllib.request.urlopen(
                f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections",
                timeout=2,
            ) as response:
                if response.status == 200:
                    print("Qdrant is ready!")
                    return
        except Exception:
            pass
        time.sleep(1)
        if (i + 1) % 5 == 0:
            print(f"Still waiting... ({i + 1}/{max_retries})")

    raise RuntimeError(
        f"Qdrant container failed to "
        f"start or become ready within {max_retries} seconds.",
    )


def split_faq_records(text: str) -> list[str]:
    """
    Split text into individual FAQ records.

    Each FAQ record starts with 'id': 'FAQ_XXX' pattern.
    This maintains the semantic integrity of each FAQ entry.

    Args:
        text: The full text content containing FAQ records.

    Returns:
        A list of FAQ record strings, each containing a complete FAQ entry.
    """
    # Pattern to match the start of a new FAQ record
    # Matches: 'id': 'FAQ_XXX' (may be at start of text or after newlines)
    pattern = r"'id':\s*'FAQ_\d+'"

    # Find all matches
    matches = list(re.finditer(pattern, text))

    if not matches:
        # If no FAQ pattern found, return the whole text as a single record
        return [text] if text.strip() else []

    # Split text at FAQ record boundaries
    records = []
    for i, match in enumerate(matches):
        start = match.start()
        # Find the end: either next FAQ record or end of text
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        record = text[start:end].strip()
        if record:
            records.append(record)

    return records


async def check_rag_initialized(
    collection_name: str = "as_faq",
) -> bool:
    """
    Check if RAG data is already initialized in Qdrant.

    This function will start Qdrant container if it's not running,
    then check if the collection exists and has data.
    """
    try:
        # Ensure Qdrant container is running
        if not check_container_running(QDRANT_CONTAINER_NAME):
            if check_container_exists(QDRANT_CONTAINER_NAME):
                # Container exists but not running, start it
                subprocess.run(
                    ["docker", "start", QDRANT_CONTAINER_NAME],
                    check=False,
                    capture_output=True,
                )
            else:
                # Container doesn't exist, need to initialize
                return False

        # Wait a bit for container to be ready
        import urllib.request

        max_retries = 10
        for i in range(max_retries):
            try:
                response = urllib.request.urlopen(
                    f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections",
                    timeout=2,
                )
                if response.status == 200:
                    break
            except Exception:
                if i < max_retries - 1:
                    time.sleep(1)
                else:
                    return False

        from qdrant_client import QdrantClient

        # Try to connect to Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [col.name for col in collections]

        if collection_name not in collection_names:
            return False

        # Check if collection has data
        collection_info = client.get_collection(collection_name)
        point_count = collection_info.points_count

        return point_count > 0
    except Exception as e:
        # If connection fails, assume not initialized
        logger.warning(f"Could not check RAG initialization status: {e}")
        return False


async def initialize_rag(
    faq_file_path: Optional[Path] = None,
    collection_name: str = "as_faq",
) -> None:
    """
    Initialize RAG data by processing FAQ file and adding to Qdrant.

    Args:
        faq_file_path: Path to FAQ file. If None, uses default file.
        collection_name: Name of the Qdrant collection.
    """
    # Start Qdrant container automatically
    start_qdrant_container()

    # Use provided file or default file
    if faq_file_path is None:
        faq_file_path = SCRIPT_DIR / "as_faq_samples.txt"

    if not faq_file_path.exists():
        raise FileNotFoundError(
            f"FAQ file not found: {faq_file_path}. "
            "Please ensure the file exists.",
        )

    print(f"Reading FAQ file: {faq_file_path}")
    with open(faq_file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Create knowledge base instance
    knowledge = SimpleKnowledge(
        embedding_store=QdrantStore(
            location=None,
            client_kwargs={
                "host": QDRANT_HOST,  # Qdrant server address
                "port": QDRANT_PORT,  # Qdrant server port
            },
            collection_name=collection_name,
            dimensions=1024,  # The dimension of the embedding vectors
        ),
        embedding_model=DashScopeTextEmbedding(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            model_name="text-embedding-v4",
        ),
    )

    print("Processing documents and adding to knowledge base...")

    # First, split by FAQ records to maintain semantic integrity
    # Each FAQ record starts with 'id': 'FAQ_XXX'
    faq_records = split_faq_records(full_text)
    print(f"Found {len(faq_records)} FAQ records")

    # Then, for each FAQ record, split if it's too long
    reader = TextReader(chunk_size=2048, split_by="char")
    all_documents = []

    for faq_record in faq_records:
        # If the FAQ record is short enough, use it as-is
        if len(faq_record) <= 2048:
            # Create a document directly from the FAQ record
            doc_id = hashlib.sha256(faq_record.encode("utf-8")).hexdigest()
            all_documents.append(
                Document(
                    id=doc_id,
                    metadata=DocMetadata(
                        content=TextBlock(type="text", text=faq_record),
                        doc_id=doc_id,
                        chunk_id=0,
                        total_chunks=1,
                    ),
                ),
            )
        else:
            # If too long, split it further using TextReader
            chunked_docs = await reader(text=faq_record)
            all_documents.extend(chunked_docs)

    await knowledge.add_documents(all_documents)
    print(
        f"Successfully added {len(all_documents)} "
        "document(s) to the knowledge base.",
    )
    print(f"Storage location: {QDRANT_STORAGE_DIR}")


async def main() -> None:
    """Main function for standalone execution."""
    # Read the FAQ samples file

    faq_file_path = SCRIPT_DIR / "as_faq_samples.txt"
    collection_name = "as_faq"
    await initialize_rag(
        faq_file_path=faq_file_path,
        collection_name=collection_name,
    )


if __name__ == "__main__":
    asyncio.run(main())
