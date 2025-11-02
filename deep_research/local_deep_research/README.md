# Local Deep Research Agent

## What This Example Demonstrates

This example demonstrates a **Local Deep Research Agent** implementation using the AgentScope framework. Unlike traditional research agents that rely solely on web search, this agent leverages a **local vector database** for knowledge retrieval, making it ideal for:

- 🔒 **Private/Confidential Research** - Keep sensitive documents local
- 📚 **Domain-Specific Research** - Build custom knowledge bases from your own documents  
- 🌐 **Offline Research** - Work without internet connectivity
- 🎯 **Precision Research** - Control exactly what sources the agent can access

The agent performs sophisticated multi-step research by:
1. Decomposing complex queries into subtasks
2. Retrieving relevant information from local vector database
3. Analyzing and synthesizing information from multiple sources
4. Generating comprehensive, well-structured research reports

This example also includes a **FastAPI backend** that exposes RESTful APIs for document management and research queries, making it easy to integrate into your applications.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           LocalDeepResearchAgent (AgentScope)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • Query Decomposition                                 │  │
│  │  • Subtask Planning                                    │  │
│  │  • Iterative Research                                  │  │
│  │  • Result Synthesis                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────┬─────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────┐      ┌─────────────────────────────┐
│   Vector Search Tool  │◄────►│    Vector Database          │
│   (Semantic Retrieval)│      │    (Milvus)                 │
└───────────────────────┘      │  ┌─────────────────────┐    │
                               │  │ Collection 1        │    │
┌───────────────────────┐      │  ├─────────────────────┤    │
│  Embedding Model      │◄────►│  │ Collection 2        │    │
│  (Text → Vectors)     │      │  ├─────────────────────┤    │
└───────────────────────┘      │  │ Collection N        │    │
                               │  └─────────────────────┘    │
                               └─────────────────────────────┘
                                        ▲
                                        │
                      ┌─────────────────┴─────────────────┐
                      │                                   │
            ┌─────────┴─────────┐          ┌─────────────┴──────────┐
            │  Document Loaders │          │   Web Crawlers         │
            │  • PDF            │          │   • FireCrawl          │
            │  • Text           │          │   • Jina               │
            │  • JSON           │          │   • Docling            │
            │  • Docling        │          │   • Crawl4AI           │
            │  • Unstructured   │          └────────────────────────┘
            └───────────────────┘
```

## 🌳 Project Structure

```
local_deep_research/
├── README.md                                # This file
├── main.py                                  # Main entry point (starts API server)
├── config.yaml                              # Configuration file (you need to create this)
├── config.yaml.example                      # Example configuration template
├── configuration.py                         # Configuration management
├── pyproject.toml                           # Project dependencies (uv/pip)
├── offline_loading.py                       # Offline document loading utilities
│
├── agent/                                   # Agent Implementation
│   ├── __init__.py
│   └── local_deep_research_agent.py        # LocalDeepResearchAgent class
│
├── api/                                     # FastAPI Application
│   ├── __init__.py
│   ├── main.py                             # API entry point
│   ├── app.py                              # FastAPI app initialization
│   ├── config.py                           # API configuration
│   ├── dependencies.py                     # Dependency injection
│   ├── models.py                           # Pydantic models for API
│   └── routers/
│       ├── __init__.py
│       ├── documents.py                    # Document management endpoints
│       └── research.py                     # Research query endpoints
│
├── built_in_prompt/                        # Agent Prompts
│   ├── promptmodule.py                     # Prompt templates
│   ├── prompt_decompose_subtask.md         # Subtask decomposition prompt
│   ├── prompt_deeper_expansion.md          # Deep expansion prompt
│   ├── prompt_deepresearch_summary_report.md  # Summary report prompt
│   ├── prompt_inprocess_report.md          # In-process report prompt
│   ├── prompt_reflect_failure.md           # Failure reflection prompt
│   ├── prompt_tool_usage_rules.md          # Tool usage guidelines
│   └── prompt_worker_additional_sys_prompt.md # Worker system prompt
│
├── embedding/                              # Embedding Models
│   ├── __init__.py
│   ├── base.py                            # Base embedding interface
│   ├── openai_embedding.py                # OpenAI embedding
│   ├── aliyun_embedding.py                # Aliyun DashScope embedding
│   ├── siliconflow_embedding.py           # Siliconflow embedding
│   └── sentence_transformer_embedding.py  # Local embedding (offline)
│
├── loader/                                 # Document & Web Loaders
│   ├── __init__.py
│   ├── base_loader.py                     # Base loader interface
│   ├── web_crawler/                       # Web crawling implementations
│   │   ├── __init__.py
│   │   ├── base.py                       # Base crawler interface
│   │   ├── firecrawl_crawler.py          # FireCrawl (recommended)
│   │   ├── jina_crawler.py               # Jina AI Reader
│   │   ├── docling_crawler.py            # Docling crawler
│   │   └── crawl4ai_crawler.py           # Crawl4AI crawler
│   └── file_loader/                       # File loading implementations
│       ├── __init__.py
│       ├── base.py                       # Base file loader
│       ├── pdf_loader.py                 # PDF files (default)
│       ├── text_loader.py                # Text/Markdown files
│       ├── json_file_loader.py           # JSON files
│       ├── docling_loader.py             # Docling loader (advanced)
│       └── unstructured_loader.py        # Unstructured loader (all formats)
│
├── vector_db/                             # Vector Database
│   ├── __init__.py
│   ├── base.py                           # Base vector DB interface
│   └── milvus.py                         # Milvus implementation
│
├── tools/                                 # Agent Tools
│   ├── __init__.py
│   └── vector_search_tool.py             # Vector search tool factory
│
├── utils/                                 # Utilities
│   ├── __init__.py
│   ├── log.py                            # Logging utilities
│   └── utils.py                          # Helper functions
│
├── scripts/                               # Utility Scripts
│   ├── README.md                         # Scripts documentation
│   ├── load_agentscope_docs.sh           # Bash script to load docs
│   ├── load_agentscope_docs.py           # Python script to load docs
│   └── urls_to_load.json                 # URL list for batch loading
│
├── tmp/                                   # Temporary files (agent working dir)
└── uploads/                               # Uploaded files storage
```

## Prerequisites

### Required
- **Python**: 3.12 or higher
- **Milvus**: Vector database (Docker recommended)
- **LLM API Key**: From one of the following:
  - [Alibaba Cloud DashScope](https://dashscope.console.aliyun.com/) (QWen models)
  - [OpenAI](https://platform.openai.com/) (GPT models)
  - Any OpenAI-compatible endpoint

### Recommended
- **Embedding API Key** (choose one):
  - [Siliconflow](https://siliconflow.cn/) (Recommended, free tier available)
  - [Alibaba Cloud DashScope](https://dashscope.console.aliyun.com/)
  - OpenAI (most expensive option)
  - Or use local embeddings (no API key needed, but slower)

### Optional (for advanced features)
- **FireCrawl API Key**: For web crawling ([Get it here](https://www.firecrawl.dev/))
- **Jina API Key**: Alternative web crawler ([Get it here](https://jina.ai/reader/))

## Installation

### 1. Install Dependencies

We recommend using `uv` (fastest) or `pip`:

#### Using uv (Recommended)
```bash
# Install uv if you haven't
pip install uv

# Install core dependencies
uv pip install -e .

# (Optional) Install all features including advanced loaders
uv pip install -e ".[all]"
```

#### Using pip
```bash
# Install core dependencies
pip install -e .

# (Optional) Install all features including advanced loaders
pip install -e ".[all]"
```

### 2. Start Milvus (Vector Database)

The easiest way is using Docker:

```bash
# Start Milvus standalone
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v milvus_data:/var/lib/milvus \
  milvusdb/milvus:latest

# Verify it's running
curl http://localhost:9091/healthz
```

For production deployments or clustering, see [Milvus documentation](https://milvus.io/docs/install_standalone-docker.md).

### 3. Configure the Application

Create a `config.yaml` file from the example:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` to configure:
- **LLM provider and model**
- **Embedding model**
- **Vector database connection**
- **File loaders and web crawlers**
- **Research parameters**

See the "Configuration" section below for details.

### 4. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Required: LLM API Key (choose based on your provider in config.yaml)
DASHSCOPE_API_KEY="your_dashscope_api_key"
# or
OPENAI_API_KEY="your_openai_api_key"

# Recommended: Embedding API Key (if using API-based embedding)
SILICONFLOW_API_KEY="your_siliconflow_api_key"

# Optional: Web crawler API keys
FIRECRAWL_API_KEY="your_firecrawl_api_key"
JINA_API_TOKEN="your_jina_api_key"

# Optional: API server settings
API_HOST="0.0.0.0"
API_PORT="8000"
API_RELOAD="true"
```

## Configuration

The `config.yaml` file has four main sections:

### 1. LLM Configuration

```yaml
provide_settings:
  llm:
    provider: "DashScope"  # Options: OpenAI, DashScope
    config:
      model: "qwen-max"  # e.g., gpt-4, qwen-max, DeepSeek-V3
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      api_key: null  # Set via DASHSCOPE_API_KEY env var
      enable_thinking: false  # Enable for compatible models
```

### 2. Embedding Model Configuration

```yaml
  embedding:
    provider: "SiliconflowEmbedding"
    # Options:
    #   - SiliconflowEmbedding (Recommended, free tier)
    #   - OpenAIEmbedding (OpenAI compatible)
    #   - AliyunEmbedding (DashScope)
    #   - SentenceTransformerEmbedding (Local, no API needed)
    config:
      model: "BAAI/bge-m3"  # Popular embedding model
      base_url: "https://api.siliconflow.cn/v1"
      api_key: null  # Set via SILICONFLOW_API_KEY env var
```

### 3. Vector Database Configuration

```yaml
  vector_db:
    provider: "Milvus"
    config:
      default_collection: "deepsearcher"  # Default collection name
      uri: "http://localhost:19530"  # Milvus server address
      token: "root:Milvus"  # Authentication (username:password)
      db: "default"  # Database name
      hybrid: false  # Enable hybrid search (vector + keyword)
```

### 4. Document Loaders & Web Crawlers

```yaml
  # File loader for local documents
  file_loader:
    provider: "PDFLoader"  # Default (no extra deps)
    # Options: PDFLoader, TextLoader, JsonFileLoader, 
    #          DoclingLoader (pip install docling),
    #          UnstructuredLoader (pip install "unstructured[all-docs]")
    config: {}

  # Web crawler for online content
  web_crawler:
    provider: "FireCrawlCrawler"  # Recommended
    # Options: FireCrawlCrawler (needs API key),
    #          JinaCrawler (needs API key),
    #          DoclingCrawler (pip install docling),
    #          Crawl4AICrawler (pip install crawl4ai)
    config: {}
```

### 5. Research Parameters

```yaml
query_settings:
  max_iter: 3  # Maximum research iterations
  max_depth: 3  # Maximum recursive search depth

load_settings:
  chunk_size: 1500  # Text chunk size for splitting
  chunk_overlap: 100  # Overlap between chunks
```

## Usage

### Option 1: Run the API Server (Recommended)

Start the FastAPI server:

```bash
python main.py
```

Or with custom port:

```bash
API_PORT=8080 python main.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

#### API Endpoints

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Upload Document:**
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/document.pdf"
```

**Load Document to Vector DB:**
```bash
curl -X POST http://localhost:8000/documents/load \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf",
    "collection_name": "my_docs",
    "chunk_size": 1500
  }'
```

**Load Website to Vector DB:**
```bash
curl -X POST http://localhost:8000/documents/load-from-website \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/article"],
    "collection_name": "web_content"
  }'
```

**Perform Research Query:**
```bash
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain the concept of attention mechanism in transformers",
    "collection_name": "research_papers",
    "max_iters": 3
  }'
```

**List Collections:**
```bash
curl http://localhost:8000/documents/collections
```

**Get Collection Info:**
```bash
curl http://localhost:8000/documents/collections/my_docs
```

### Option 2: Use as Python Library

```python
import asyncio
from agentscope.message import Msg
from agentscope import setup_logger
from local_deep_research.agent import LocalDeepResearchAgent
from local_deep_research.embedding import SiliconflowEmbedding
from local_deep_research.vector_db import Milvus

# Setup
setup_logger(level="INFO")

# Initialize components
embedding_model = SiliconflowEmbedding(
    model="BAAI/bge-m3",
    api_key="your_api_key"
)

vector_db = Milvus(
    uri="http://localhost:19530",
    token="root:Milvus"
)

# Configure LLM
llm_config = {
    "config_name": "qwen-config",
    "model_type": "dashscope_chat",
    "model_name": "qwen-max",
    "api_key": "your_dashscope_api_key"
}

# Create agent
agent = LocalDeepResearchAgent(
    name="LocalResearcher",
    sys_prompt="You are a helpful research assistant.",
    model_config_name="qwen-config",
    embedding_model=embedding_model,
    vector_db=vector_db,
    tmp_file_storage_dir="./tmp"
)

# Perform research
async def main():
    response = await agent(
        Msg(
            name="user",
            content="What are the latest advancements in multimodal LLMs?",
            role="user"
        )
    )
    print(response.content)

asyncio.run(main())
```

### Quick Start: Load Sample Documents

We provide scripts to quickly load documentation into your vector database:

```bash
# 1. Edit the URL list
nano scripts/urls_to_load.json

# 2. Start the API server (in another terminal)
python main.py

# 3. Run the loading script
./scripts/load_agentscope_docs.sh
```

See `scripts/README.md` for more details.

## Advanced Features

### 1. Hybrid Search (Experimental)

Enable hybrid search (vector + keyword) in `config.yaml`:

```yaml
vector_db:
  config:
    hybrid: true  # Combines semantic and keyword search
```

### 2. Custom File Loaders

The agent supports multiple file formats through different loaders:

| Loader | Formats | Installation |
|--------|---------|--------------|
| **PDFLoader** | PDF, MD, TXT | Built-in (default) |
| **TextLoader** | TXT, MD | Built-in |
| **JsonFileLoader** | JSON | Built-in |
| **DoclingLoader** | [Many formats](https://docling-project.github.io/docling/usage/supported_formats/) | `pip install docling` |
| **UnstructuredLoader** | PDF, Word, Excel, PPT, etc. | `pip install "unstructured[all-docs]"` |

Configure in `config.yaml`:

```yaml
provide_settings:
  file_loader:
    provider: "DoclingLoader"  # Change to your preferred loader
    config: {}
```

### 3. Custom Web Crawlers

Choose the best web crawler for your needs:

| Crawler | Pros | Cons | Installation |
|---------|------|------|--------------|
| **FireCrawl** | Best quality, most reliable | Requires API key | Built-in |
| **JinaCrawler** | Simple, fast | Requires API key | Built-in |
| **DoclingCrawler** | Free, offline | Complex setup | `pip install docling` |
| **Crawl4AICrawler** | Feature-rich | Requires browser setup | `pip install crawl4ai` |

Configure in `config.yaml`:

```yaml
provide_settings:
  web_crawler:
    provider: "FireCrawlCrawler"  # Change to your preferred crawler
    config: {}
```

### 4. Local Embedding (Offline)

For completely offline research, use local embeddings:

```bash
# Install sentence-transformers
pip install sentence-transformers
```

Configure in `config.yaml`:

```yaml
provide_settings:
  embedding:
    provider: "SentenceTransformerEmbedding"
    config:
      model: "sentence-transformers/all-MiniLM-L6-v2"
      device: "cpu"  # or "cuda" for GPU
```

## Troubleshooting

### Issue: Milvus connection failed

**Solution:**
1. Check if Milvus is running: `curl http://localhost:9091/healthz`
2. Verify URI in `config.yaml` matches your Milvus setup
3. Check Docker logs: `docker logs milvus-standalone`

### Issue: API key not found

**Solution:**
1. Ensure `.env` file exists in project root
2. Check environment variable names match your provider
3. Restart the API server after updating `.env`

### Issue: Import errors

**Solution:**
1. Install missing dependencies: `pip install -e ".[all]"`
2. Check Python version: `python --version` (must be 3.12+)
3. Activate virtual environment if using one

### Issue: Document loading fails

**Solution:**
1. Check file format is supported by your configured loader
2. Verify file path is correct and accessible
3. Try with a different loader (e.g., DoclingLoader or UnstructuredLoader)

### Issue: Research query returns empty results

**Solution:**
1. Verify documents are loaded: `curl http://localhost:8000/documents/collections/your_collection`
2. Check collection name matches in query
3. Ensure embedding model is the same one used to load documents

## Contributing

This example is part of [AgentScope Samples](https://github.com/modelscope/agentscope-samples). Contributions are welcome!

To contribute:
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

Please follow the contribution guidelines in [CONTRIBUTING.md](../../CONTRIBUTING.md).

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.

## Acknowledgments

- Built with [AgentScope](https://github.com/modelscope/agentscope) framework
- Vector storage powered by [Milvus](https://milvus.io/)
- Inspired by deep research methodologies and RAG (Retrieval-Augmented Generation) techniques

## Related Examples

- [agent_deep_research](../agent_deep_research/) - Web-based deep research agent using MCP
- [qwen_langgraph_search_fullstack_runtime](../qwen_langgraph_search_fullstack_runtime/) - LangGraph-based research system

## Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/modelscope/agentscope-samples/issues)
- **Documentation**: [AgentScope Docs](https://doc.agentscope.io/)
- **Discord**: [Join our community](https://discord.gg/eYMpfnkG8h)
- **DingTalk**: Scan QR code in main README (for Chinese users)

---

**Happy Researching! 🔍📚**

