<h2 align="center">Alias for Question Answering</h2>

Alias-QA is a question-answering agent that integrates RAG (Retrieval-Augmented Generation) and GitHub MCP tools, capable of answering user questions based on both a private knowledge base and GitHub code repositories.

## Environment Setup

Before using Alias-QA, you need to set the following environment variables:

```bash
export DASHSCOPE_API_KEY=your_dashscope_api_key
export GITHUB_TOKEN=your_github_token
```

**GITHUB_TOKEN**: Used to access GitHub MCP tools (search repositories, code, etc.). For how to obtain it, please refer to the [GitHub documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

## Using Custom Knowledge Base

If you want to use your own documents to build a knowledge base, refer to the following steps.


### Usage Steps

1. **Prepare Your Document File**

    Place your document file in the text format supported in the `alias/agent/agents/qa_agent_utils` directory, or specify a file path.
2. **Modify Script Parameters**

   Edit the `main()` function in `create_rag_file.py` and change `faq_file_path` to your file path:

   ```python
   async def main() -> None:
       """Main function for standalone execution."""
       # Read the FAQ samples file

       faq_file_path = SCRIPT_DIR / "as_faq_samples.txt"
       collection_name = "as_faq"
       await initialize_rag(
           faq_file_path=faq_file_path,
           collection_name=collection_name,
       )
   ```
3. **Run the Script**

   ```bash
   python alias/agent/agents/qa_agent_utils/create_rag_file.py
   ```

   The script will automatically:

   - Start the Qdrant vector database (if not running)
   - Read and process your document file
   - Chunk the documents and generate embedding vectors
   - Store them in the Qdrant database

### Important Notes

#### Default Behavior

If no file path is specified, the script will default to processing the `as_faq_samples.txt` file and store the processed data at the following path: `/alias/agent/agents/qa_agent_utils/qdrant_storage/collections/as_faq`

- In this path, `as_faq` is the value of `collection_name`
- Running this script repeatedly will **continually append** processed file content to `collections/as_faq`

#### Creating and Using Different Collections

1. **Create a New Collection**

   You can create a new collection by editing the `main()` function in `create_rag_file.py` and modifying the `collection_name` parameter:

   ```python
   collection_name = "your_own_collection_name"
   ```
2. **Switch to a Different Collection**

   In `/alias/agent/tools/add_qa_tools.py`, when referring to the knowledge base through `knowledge = SimpleKnowledge(...)`, you can switch to a different collection by modifying the `collection_name` parameter:

   ```python
   collection_name = "collection_name_you_want_to_use"
   ```

### More Information

`create_rag_file.py` is a demo implementation of RAG functionality in AgentScope. For more advanced operations and customization options regarding RAG, please refer to the [AgentScope RAG Official Documentation](https://doc.agentscope.io/zh_CN/tutorial/task_rag.html), including:

- Multimodal RAG
- Custom Reader, Knowledge, and Store components
- Agentic vs. Generic RAG
