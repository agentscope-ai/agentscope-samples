# User Profiling Service Docker Deployment

This directory contains Docker deployment files for the User Profiling Service.

## Files

- `Dockerfile` - Docker image definition with supervisord process management
- `docker-compose.yml` - Docker Compose configuration
- `supervisord.conf` - Supervisord configuration for process management
- `deploy.sh` - Deployment script

## Quick Start

### Using Docker Compose (Recommended)

```bash
cd alias/memory_service/docker
docker compose up -d
docker compose logs -f user-profiling-service
docker compose down
```

### Using Deployment Script

```bash
cd alias/memory_service/docker
./deploy.sh start          # Start service
./deploy.sh stop           # Stop service
./deploy.sh restart        # Restart service
./deploy.sh logs           # View logs
./deploy.sh clean          # Clean up everything
./deploy.sh env-check      # Check environment variables
```

## Service Information

After deployment, the service will be available at:

- **Base URL**: `http://localhost:6380`
- **API Documentation**: `http://localhost:6380/docs`
- **Health Check**: `http://localhost:6380/health`

## Deployment Versions

- **Start**: `./deploy.sh start`
- **Services**:
  - User Profiling Service: `http://localhost:6380`
  - Redis: `redis://localhost:7000`
  - Qdrant API: `http://localhost:6333`
  - Qdrant Dashboard: `http://localhost:6333/dashboard`


## Environment Variables

Create a `.env` file in the root directory:

```bash
# Required
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL_4_MEMORY=gpt-4o

# Optional
DASHSCOPE_MODEL=gpt-4o
USER_PROFILING_REDIS_PASSWORD=your_redis_password
LOG_LEVEL=INFO
PYTHONPATH=/app
```

Check environment variables: `./deploy.sh env-check`

## Logs

- **Local logs**: `../../../logs/` (relative to docker directory)
- **Container logs**: `docker logs user-profiling-service`
- **Service logs**: `/app/logs/memory_service.out.log` and `/app/logs/memory_service.err.log` (inside container)

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
lsof -i :6380
docker stop user-profiling-service
```

**Build fails:**
```bash
./deploy.sh clean
./deploy.sh build
```

**Service not responding:**
```bash
docker logs user-profiling-service
docker ps -a
docker exec -it user-profiling-service supervisorctl status
```

### Useful Commands

```bash
# Container management
docker exec -it user-profiling-service bash
docker stats user-profiling-service
docker inspect user-profiling-service

# Supervisord management
docker exec -it user-profiling-service supervisorctl status
docker exec -it user-profiling-service supervisorctl restart memory-service
```

## Process Management

The service uses **supervisord** for automatic restart and process monitoring. Logs are managed automatically.

## Production Notes

For production deployment, consider:
- Using a reverse proxy (nginx, traefik)
- Setting up SSL/TLS certificates
- Configuring proper logging and monitoring
- Using Docker secrets for sensitive data
- Setting resource limits in docker-compose.yml
