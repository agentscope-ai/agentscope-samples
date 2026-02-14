#!/bin/bash
# -*- coding: utf-8 -*-
# AgentScope Documentation Loader - Bash Version
#
# Use curl to call API to load webpages into vector database

set -e  # Exit on error

# ==================== Configuration ====================

# API Configuration
API_HOST="localhost"
API_PORT="8000"
API_ENDPOINT="http://${API_HOST}:${API_PORT}/documents/load-from-website"

# Collection Configuration
COLLECTION_NAME="agent_scope_docs"
COLLECTION_DESCRIPTION="AgentScope Documentation"
FORCE_NEW_COLLECTION=false

# Loading Configuration
CHUNK_SIZE=1500
CHUNK_OVERLAP=100
BATCH_SIZE=10

# JSON File Path
URLS_JSON_FILE="scripts/urls_to_load.json"

# ==================== Functions ====================

print_header() {
    echo "============================================================"
    echo "AgentScope Documentation Loader (Bash Version)"
    echo "============================================================"
}

check_json_file() {
    if [ ! -f "$URLS_JSON_FILE" ]; then
        echo ""
        echo "✗ Error: JSON file not found: $URLS_JSON_FILE"
        echo ""
        echo "Please create $URLS_JSON_FILE with the following format:"
        echo '['
        echo '  {'
        echo '    "url": "https://doc.agentscope.io/tutorial/task_model.html",'
        echo '    "title": "Model - AgentScope"'
        echo '  },'
        echo '  {'
        echo '    "url": "https://runtime.agentscope.io/en/quickstart.html",'
        echo '    "title": "Quickstart"'
        echo '  }'
        echo ']'
        exit 1
    fi
}

check_api_health() {
    echo ""
    echo "Checking API health..."

    health_response=$(curl -s "http://${API_HOST}:${API_PORT}/health" 2>/dev/null || echo "error")

    if [ "$health_response" = "error" ]; then
        echo "✗ Error: Cannot connect to API at http://${API_HOST}:${API_PORT}"
        echo "Please make sure the API server is running."
        exit 1
    fi

    echo "✓ API is healthy"
}

load_urls_from_json() {
    # Use jq to extract URL list (if jq is installed)
    if command -v jq &> /dev/null; then
        urls=$(jq -r '.[].url' "$URLS_JSON_FILE" 2>/dev/null || echo "error")
        if [ "$urls" = "error" ]; then
            echo "✗ Error: Failed to parse JSON file"
            exit 1
        fi
        url_count=$(echo "$urls" | wc -l | tr -d ' ')
    else
        # If jq is not available, use simple grep method (not very accurate but works)
        url_count=$(grep -o '"url"' "$URLS_JSON_FILE" | wc -l | tr -d ' ')
    fi

    echo "$url_count"
}

show_info() {
    local url_count=$1

    echo ""
    echo "Collection: $COLLECTION_NAME"
    echo "Description: $COLLECTION_DESCRIPTION"
    echo ""
    echo "URLs to load: $url_count"
    echo ""
    echo "Configuration:"
    echo "  - API Endpoint: $API_ENDPOINT"
    echo "  - Chunk size: $CHUNK_SIZE"
    echo "  - Chunk overlap: $CHUNK_OVERLAP"
    echo "  - Batch size: $BATCH_SIZE"
    echo "  - Force new collection: $FORCE_NEW_COLLECTION"
}

confirm_load() {
    echo ""
    read -p "Proceed with loading? (y/n): " choice
    case "$choice" in
        y|Y ) return 0;;
        * ) echo "Cancelled."; exit 0;;
    esac
}

build_request_body() {
    # Read JSON file and extract URL array
    # Build request body
    cat > /tmp/load_request.json <<EOF
{
  "urls": $(jq '[.[].url]' "$URLS_JSON_FILE" 2>/dev/null || echo '["error"]'),
  "collection_name": "$COLLECTION_NAME",
  "collection_description": "$COLLECTION_DESCRIPTION",
  "force_new_collection": $FORCE_NEW_COLLECTION,
  "chunk_size": $CHUNK_SIZE,
  "chunk_overlap": $CHUNK_OVERLAP,
  "batch_size": $BATCH_SIZE
}
EOF
}

build_request_body_simple() {
    # If jq is not available, build manually (read from JSON file)
    python3 -c "
import json
import sys

try:
    with open('$URLS_JSON_FILE', 'r') as f:
        data = json.load(f)
    urls = [item['url'] for item in data if 'url' in item]

    request = {
        'urls': urls,
        'collection_name': '$COLLECTION_NAME',
        'collection_description': '$COLLECTION_DESCRIPTION',
        'force_new_collection': $FORCE_NEW_COLLECTION,
        'chunk_size': $CHUNK_SIZE,
        'chunk_overlap': $CHUNK_OVERLAP,
        'batch_size': $BATCH_SIZE
    }

    with open('/tmp/load_request.json', 'w') as f:
        json.dump(request, f, indent=2)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
}

call_api() {
    echo ""
    echo "Starting to load website content..."
    echo "------------------------------------------------------------"

    # Send POST request
    response=$(curl -s -X POST "$API_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d @/tmp/load_request.json)

    # Check response
    status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null || echo "error")

    if [ "$status" = "success" ]; then
        echo "------------------------------------------------------------"
        echo ""
        echo "✓ Successfully loaded all URLs into the vector database!"
        echo "✓ Collection: $COLLECTION_NAME"

        # Try to extract number of processed URLs
        urls_processed=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('urls_processed', 'N/A'))" 2>/dev/null || echo "N/A")
        echo "✓ Total URLs processed: $urls_processed"

        # Clean up temporary files
        rm -f /tmp/load_request.json
    else
        echo "------------------------------------------------------------"
        echo ""
        echo "✗ Error loading website content"
        echo "Response: $response"
        rm -f /tmp/load_request.json
        exit 1
    fi
}

# ==================== Main Process ====================

main() {
    print_header

    # Check JSON file
    check_json_file

    # Check API health
    check_api_health

    # Load URL count
    url_count=$(load_urls_from_json)

    # Show information
    show_info "$url_count"

    # Confirm
    confirm_load

    # Build request body
    if command -v jq &> /dev/null; then
        build_request_body
    else
        build_request_body_simple
    fi

    # Call API
    call_api
}

# Run main function
main
