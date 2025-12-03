#!/bin/bash

# Memory Service Deployment Script

set -e

SERVICE_NAME="memory-service"
IMAGE_NAME="alias-memory-service-v1"
COMPOSE_FILE="docker-compose.yml"
LOG_DIR="../../../logs"
ENV_FILE="./.env"
# Ensure .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create .env in $(pwd)"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to create logs directory
create_logs_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        print_status "Creating logs directory..."
        mkdir -p "$LOG_DIR"
        print_success "Logs directory created: $LOG_DIR"
    fi
}

# Function to check environment variables
check_env_vars() {
    print_status "Checking environment variables..."

    # Check for required environment variables
    local missing_vars=()

    if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
        missing_vars+=("DASHSCOPE_API_KEY")
    fi

    if [ -z "${DASHSCOPE_API_BASE_URL:-}" ]; then
        missing_vars+=("DASHSCOPE_API_BASE_URL")
    fi

    if [ -z "${DASHSCOPE_MODEL_4_MEMORY:-}" ]; then
        missing_vars+=("DASHSCOPE_MODEL_4_MEMORY")
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_warning "Missing environment variables: ${missing_vars[*]}"
        print_status "Please set these variables in your .env file or environment:"
        for var in "${missing_vars[@]}"; do
            echo "  export $var=your_value_here"
        done
        echo ""
        print_status "Example .env file:"
        echo "  DASHSCOPE_API_KEY=your_api_key_here"
        echo "  DASHSCOPE_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"
        echo "  DASHSCOPE_MODEL_4_MEMORY=gpt-4o"
        echo "  DASHSCOPE_MODEL=gpt-4o"
        echo "  USER_PROFILING_REDIS_PASSWORD=your_redis_password"
        echo ""
    else
        print_success "All required environment variables are set"
    fi
}

# Function to build the image
build_image() {
    print_status "Building Docker image..."
    cd ../../../
    docker build -t "$IMAGE_NAME" -f alias/memory_service/docker/Dockerfile .
    cd alias/memory_service/docker
    print_success "Docker image built successfully"
}

# Function to build the image without cache
build_image_no_cache() {
    print_status "Building Docker image (no cache)..."
    cd ../../../
    docker build --no-cache -t "$IMAGE_NAME" -f alias/memory_service/docker/Dockerfile .
    cd alias/memory_service/docker
    print_success "Docker image built successfully (no cache)"
}

start_service() {
    print_status "Starting Memory Service..."
    create_logs_dir
    check_env_vars

    # 🔥 Auto-build image (essential for development mode!)
    print_status "Building Docker image..."
    cd ../../../
    docker build -t "$IMAGE_NAME" -f alias/memory_service/docker/Dockerfile .
    cd alias/memory_service/docker

    print_status "Starting with Redis and Qdrant (basic version)..."

    # Start service
    docker compose up -d

    # Wait for startup
    sleep 5

    # Verify port
    if lsof -i :6380 > /dev/null 2>&1; then
        print_success "Service is listening on port 6380!"
    else
        print_warning "Port 6380 is NOT listening. Check logs!"
    fi

    print_status "Service URL: http://localhost:6380"
    print_status "Health check: http://localhost:6380/health"
}

# Function to stop the service
stop_service() {
    print_status "Stopping Memory Service..."
    docker compose down
    print_success "Memory Service stopped"
}


restart_service() {
    print_status "Rebuilding and restarting service..."
    create_logs_dir
    check_env_vars

    # 🔥 Auto-build
    cd ../../../
    docker build -t "$IMAGE_NAME" -f alias/memory_service/docker/Dockerfile .
    cd alias/memory_service/docker

    # Down first then up (ensure using new image)
    docker compose down
    docker compose up -d

    sleep 5
    print_success "Service restarted with new code!"
}

# Function to show logs
show_logs() {
    print_status "Showing service logs..."
    docker compose logs -f "$SERVICE_NAME"
}

# Function to show status
show_status() {
    print_status "Service status:"
    docker compose ps

    print_status "Container logs (last 10 lines):"
    docker compose logs --tail=10 "$SERVICE_NAME"
}

# Function to clean up
cleanup() {
    print_warning "This will remove all containers, images, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up..."
        docker compose down -v --rmi all
        docker rmi "$IMAGE_NAME" 2>/dev/null || true
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to install dependencies
install_deps() {
    print_status "Installing Python dependencies..."

    if [ "$1" = "graph" ]; then
        print_status "Installing with graph support..."
        pip install -e .[graph]
    elif [ "$1" = "full" ]; then
        print_status "Installing with full features..."
        pip install -e .[full]
    else
        print_status "Installing basic dependencies..."
        pip install -e .
    fi

    print_success "Dependencies installed successfully"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    pip install -e .[dev]
    pytest tests/ -v
}

# Function to show help
show_help() {
    echo "Memory Service Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build              Build Docker image"
    echo "  build-no-cache     Build Docker image without cache"
    echo "  start [basic|full] Start the service (with optional support)"
    echo "  stop               Stop the service"
    echo "  restart [basic|full] Restart the service (with optional support)"
    echo "  logs               Show service logs"
    echo "  status             Show service status"
    echo "  clean              Clean up all containers and images"
    echo "  install [graph|full] Install Python dependencies"
    echo "  test               Run tests"
    echo "  env-check          Check environment variables"
    echo "  help               Show this help message"
    echo ""
    echo "Start Options:"
    echo "  basic              Start with Redis and Qdrant (default)"
    echo "  full               Start with Redis, Qdrant, and Neo4j"
    echo ""
    echo "Examples:"
    echo "  $0 build           # Build Docker image with cache"
    echo "  $0 build-no-cache  # Build Docker image without cache"
    echo "  $0 start           # Start with Redis and Qdrant (basic)"
    echo "  $0 start basic     # Start with Redis and Qdrant"
    echo "  $0 start full      # Start with Redis, Qdrant, and Neo4j"
    echo "  $0 install full    # Install with all features"
    echo "  $0 logs            # View service logs"
}

# Main script logic
main() {
    check_docker

    case "${1:-help}" in
        build)
            build_image
            ;;
        build-no-cache)
            build_image_no_cache
            ;;
        start)
            start_service "$2"
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service "$2"
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        clean)
            cleanup
            ;;
        install)
            install_deps "$2"
            ;;
        test)
            run_tests
            ;;
        env-check)
            check_env_vars
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"