# AgentScope Documentation Loader

Quick script to load AgentScope documentation into the vector database.

## Usage

### 1. Edit JSON File

Edit the `urls_to_load.json` file and add all URLs you want to load:

```json
[
  {
    "url": "https://runtime.agentscope.io/en/quickstart.html",
    "title": "Quickstart - AgentScope Runtime"
  },
  {
    "url": "https://doc.agentscope.io/tutorial/task_model.html",
    "title": "Model - AgentScope"
  },
  {
    "url": "https://runtime.agentscope.io/en/install.html",
    "title": "Installation Guide"
  }
]
```

**Note**:
- The JSON file should be an array
- Each object must contain a `url` field
- The `title` field is optional and only for documentation purposes

### 2. Start API Server

Make sure the API server is running:

```bash
# In the local_deep_research directory
cd /path/to/local_deep_research

# Activate virtual environment
source .venv/bin/activate

# Start API server
python -m local_deep_research.api.main
# Or use uvicorn
uvicorn local_deep_research.api.app:app --host 0.0.0.0 --port 8000
```

### 3. Run Bash Script (Recommended)

```bash
# In the local_deep_research directory
cd /path/to/local_deep_research

# Run the script
./scripts/load_agentscope_docs.sh
```

The script will:
1. Check API server health
2. Read the `urls_to_load.json` file
3. Display the number of URLs to load
4. Request confirmation
5. Call the API to load into vector database

### 4. (Optional) Run Python Script

If you prefer using the Python script:

```bash
# In the local_deep_research directory
cd /path/to/local_deep_research

# Activate virtual environment
source .venv/bin/activate

# Run the script
python scripts/load_agentscope_docs.py
```

## Configuration Options

### Bash Script Configuration

Edit the configuration in `load_agentscope_docs.sh`:

```bash
# API Configuration
API_HOST="localhost"
API_PORT="8000"

# Collection Configuration
COLLECTION_NAME="agent_scope_docs"
COLLECTION_DESCRIPTION="AgentScope Documentation"
FORCE_NEW_COLLECTION=false

# Loading Configuration
CHUNK_SIZE=1500
CHUNK_OVERLAP=100
BATCH_SIZE=256
```

### Python Script Configuration

Edit the configuration in `load_agentscope_docs.py`:

- `COLLECTION_NAME`: Collection name (default: `agent_scope_docs`)
- `COLLECTION_DESCRIPTION`: Collection description
- `URLS_JSON_FILE`: JSON file path (default: `scripts/urls_to_load.json`)
- `CHUNK_SIZE`: Text chunk size (default: 1500)
- `CHUNK_OVERLAP`: Text chunk overlap (default: 100)
- `BATCH_SIZE`: Batch processing size (default: 256)
- `FORCE_NEW_COLLECTION`: Force create new collection (default: False)

## Files Description

- `load_agentscope_docs.sh` - Bash version script (recommended, no dependencies needed)
- `load_agentscope_docs.py` - Python version script
- `urls_to_load.json` - URL list configuration file (you need to edit this file)
- `README.md` - This documentation file

## Dependencies

### Bash Script Dependencies
- `curl` - Send HTTP requests
- `jq` - (Optional) JSON parsing; if not available, will use Python as fallback
- `python3` - Used for JSON processing (if jq is not available)

### Python Script Dependencies
- Requires `local_deep_research` package and its dependencies

## Important Notes

- Make sure `config.yaml` file is properly configured
- Ensure vector database and embedding model are correctly configured
- Ensure API server is running (http://localhost:8000)
- Collection will be created automatically on first run
- If you need to recreate the collection, set `FORCE_NEW_COLLECTION` to `true`
- JSON file must be valid JSON format

## Example Output

```
============================================================
AgentScope Documentation Loader (Bash Version)
============================================================

Checking API health...
✓ API is healthy

Collection: agent_scope_docs
Description: AgentScope Documentation

URLs to load: 458

Configuration:
  - API Endpoint: http://localhost:8000/documents/load-from-website
  - Chunk size: 1500
  - Chunk overlap: 100
  - Batch size: 256
  - Force new collection: false

Proceed with loading? (y/n): y

Starting to load website content...
------------------------------------------------------------
------------------------------------------------------------

✓ Successfully loaded all URLs into the vector database!
✓ Collection: agent_scope_docs
✓ Total URLs processed: 458
```

