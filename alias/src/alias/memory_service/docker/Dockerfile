FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the service files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Install memory_service package with its dependencies (including reme_ai)
RUN pip install --no-cache-dir -e alias/memory_service/

# Create logs directory
RUN mkdir -p /app/logs

# Copy supervisord configuration
COPY alias/memory_service/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port
EXPOSE 6380

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6380/health || exit 1

# Run the service with supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]