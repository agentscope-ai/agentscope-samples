#!/bin/bash

# Start script for alias.memory_service.service.app.server
# This script checks and starts Redis and Qdrant services before starting the memory service

set -e  # Exit on error

# Function to print messages
print_info() {
    echo "[INFO] $1"
}

print_warn() {
    echo "[WARN] $1"
}

print_error() {
    echo "[ERROR] $1"
}

# Function to load .env file
load_env_file() {
    local env_file="$1"
    local script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

    # If no custom path provided, use default: parent directory (.env file)
    if [ -z "$env_file" ]; then
        env_file="$(dirname "$script_dir")/.env"
    fi

    if [ -f "$env_file" ]; then
        print_info "Loading environment variables from $env_file"
        # Export variables from .env file, ignoring comments and empty lines
        set -a
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue

            # Export the variable
            export "$line" 2>/dev/null || true
        done < "$env_file"
        set +a
    else
        print_warn ".env file not found at $env_file, using default environment variables"
    fi
}

# Parse command line arguments
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file|-e)
            ENV_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -e, --env-file PATH    Path to .env file (default: ../.env)"
            echo "  -h, --help             Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Load .env file before reading configuration
load_env_file "$ENV_FILE"

# Configuration (after loading .env)
REDIS_HOST="${USER_PROFILING_REDIS_SERVER:-localhost}"
REDIS_PORT="${USER_PROFILING_REDIS_PORT:-6379}"
QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"

REDIS_CONTAINER_NAME="user-profiling-redis"
QDRANT_CONTAINER_NAME="user-profiling-qdrant"

# Function to check if a port is open
check_port() {
    local host=$1
    local port=$2
    timeout 1 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null
}

# Function to check if Redis is running
check_redis() {
    if check_port "$REDIS_HOST" "$REDIS_PORT"; then
        # Try to ping Redis
        if command -v redis-cli &> /dev/null; then
            if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null; then
                return 0
            fi
        else
            # If redis-cli is not available, just check if port is open
            return 0
        fi
    fi
    return 1
}

# Function to check if Qdrant is running
check_qdrant() {
    # First check if port is open
    if check_port "$QDRANT_HOST" "$QDRANT_PORT"; then
        # Try to check Qdrant health endpoint
        if curl -s -f "http://$QDRANT_HOST:$QDRANT_PORT/health" &> /dev/null; then
            return 0
        fi
        # If port is open but health check fails, still consider it running
        # (port being allocated usually means service is running)
        return 0
    fi
    return 1
}

# Function to check if Docker is available
check_docker() {
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            return 0
        fi
    fi
    return 1
}

# Function to start Redis using Docker
start_redis_docker() {
    print_info "Starting Redis container..."

    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        # Container exists, check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
            print_info "Redis container is already running."
            return 0
        else
            print_info "Starting existing Redis container..."
            docker start "$REDIS_CONTAINER_NAME"
        fi
    else
        # Create and start new container
        print_info "Creating and starting new Redis container..."
        docker run -d \
            --name "$REDIS_CONTAINER_NAME" \
            -p "${REDIS_PORT}:6379" \
            -v redis_data:/data \
            redis:latest \
            redis-server --appendonly yes
    fi

    # Wait for Redis to be ready
    print_info "Waiting for Redis to be ready..."
    max_retries=30
    for i in $(seq 1 $max_retries); do
        if check_redis; then
            print_info "Redis is ready!"
            return 0
        fi
        sleep 1
        if [ $((i % 5)) -eq 0 ]; then
            print_warn "Still waiting for Redis... ($i/$max_retries)"
        fi
    done

    print_error "Redis failed to start within $max_retries seconds."
    return 1
}

# Function to start Qdrant using Docker
start_qdrant_docker() {
    print_info "Starting Qdrant container..."

    # Check if port is already in use by another process/container
    if check_port "$QDRANT_HOST" "$QDRANT_PORT"; then
        print_warn "Port $QDRANT_PORT is already in use. Checking if it's a Qdrant service..."
        # Check if it's our container
        if docker ps --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
            print_info "Qdrant container is already running."
            return 0
        fi
        # Check if any container is using this port
        if docker ps --format '{{.Names}} {{.Ports}}' | grep -q ":$QDRANT_PORT"; then
            print_warn "Port $QDRANT_PORT is in use by another container. Assuming Qdrant is running."
            return 0
        fi
        print_warn "Port $QDRANT_PORT is in use but not by our container. Please check manually."
        return 1
    fi

    # Create storage directory if it doesn't exist
    QDRANT_STORAGE_DIR="${HOME}/.qdrant_storage"
    mkdir -p "$QDRANT_STORAGE_DIR"

    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
        # Container exists, check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
            print_info "Qdrant container is already running."
            return 0
        else
            print_info "Starting existing Qdrant container..."
            docker start "$QDRANT_CONTAINER_NAME"
        fi
    else
        # Create and start new container
        print_info "Creating and starting new Qdrant container..."
        docker run -d \
            --name "$QDRANT_CONTAINER_NAME" \
            -p "${QDRANT_PORT}:6333" \
            -p "6334:6334" \
            -v "${QDRANT_STORAGE_DIR}:/qdrant/storage" \
            qdrant/qdrant:latest
    fi

    # Wait for Qdrant to be ready
    print_info "Waiting for Qdrant to be ready..."
    max_retries=30
    for i in $(seq 1 $max_retries); do
        if check_qdrant; then
            print_info "Qdrant is ready!"
            return 0
        fi
        sleep 1
        if [ $((i % 5)) -eq 0 ]; then
            print_warn "Still waiting for Qdrant... ($i/$max_retries)"
        fi
    done

    print_error "Qdrant failed to start within $max_retries seconds."
    return 1
}

# Main execution
main() {
    print_info "Starting Memory Service..."
    print_info "Checking dependencies..."

    # Check Redis
    print_info "Checking Redis at $REDIS_HOST:$REDIS_PORT..."
    if check_redis; then
        print_info "Redis is already running."
    else
        print_warn "Redis is not running."
        if check_docker; then
            start_redis_docker || exit 1
        else
            print_error "Docker is not available. Please start Redis manually or install Docker."
            exit 1
        fi
    fi

    # Check Qdrant
    print_info "Checking Qdrant at $QDRANT_HOST:$QDRANT_PORT..."
    if check_qdrant; then
        print_info "Qdrant is already running."
    else
        print_warn "Qdrant is not running."
        if check_docker; then
            start_qdrant_docker || exit 1
        else
            print_error "Docker is not available. Please start Qdrant manually or install Docker."
            exit 1
        fi
    fi

    # Start the memory service
    print_info "All dependencies are ready. Starting memory service..."
    print_info "Running: python -m alias.memory_service.service.app.server"

    # Set environment variables if not already set
    export USER_PROFILING_REDIS_SERVER="${USER_PROFILING_REDIS_SERVER:-localhost}"
    export USER_PROFILING_REDIS_PORT="${USER_PROFILING_REDIS_PORT:-6379}"
    export QDRANT_HOST="${QDRANT_HOST:-localhost}"
    export QDRANT_PORT="${QDRANT_PORT:-6333}"

    # Run the service
    python -m alias.memory_service.service.app.server
}

# Run main function
main "$@"

