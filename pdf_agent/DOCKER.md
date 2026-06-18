# 🐳 Docker Deployment Guide

This guide covers building, running, and deploying the PDF Agent using Docker.

## Prerequisites

- [Docker](https://www.docker.com/get-started) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v1.29+)
- Groq API Key (get from [Groq Console](https://console.groq.com/))

## Quick Start

### 1. Set Up Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your Groq API key
# Windows (PowerShell)
notepad .env

# Linux/Mac
nano .env
```

### 2. Build and Run with Docker Compose

```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f pdf-agent
```

The application will be available at: **http://localhost:8501**

### 3. Stop the Application

```bash
docker-compose down
```

---

## Manual Docker Build

If you prefer to build and run manually without docker-compose:

### Build

```bash
docker build -t pdf-agent:latest .
```

### Run

```bash
docker run -d \
  --name pdf_agent \
  -p 8501:8501 \
  -v "$(pwd)/data/uploads:/app/data/uploads" \
  -v "$(pwd)/data/chroma_db:/app/data/chroma_db" \
  -v "$(pwd)/data/logs:/app/data/logs" \
  -e GROQ_API_KEY="your_api_key_here" \
  pdf-agent:latest
```

### Access Logs

```bash
docker logs -f pdf_agent
```

### Stop

```bash
docker stop pdf_agent
docker rm pdf_agent
```

---

## Production Deployment

### Using Docker Compose for Production

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  pdf-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pdf_agent_prod
    restart: always
    ports:
      - "8501:8501"
    volumes:
      - pdf_uploads:/app/data/uploads
      - pdf_chroma_db:/app/data/chroma_db
      - pdf_logs:/app/data/logs
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - STREAMLIT_LOGGER_LEVEL=warning
      - LOG_LEVEL=WARNING
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  pdf_uploads:
  pdf_chroma_db:
  pdf_logs:

networks:
  pdf-agent-network:
    driver: bridge
```

Deploy with:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Using Cloud Platforms

#### **AWS ECS**

1. Push image to ECR:
```bash
aws ecr create-repository --repository-name pdf-agent
docker tag pdf-agent:latest <aws_account_id>.dkr.ecr.<region>.amazonaws.com/pdf-agent:latest
docker push <aws_account_id>.dkr.ecr.<region>.amazonaws.com/pdf-agent:latest
```

2. Create ECS task definition and service

#### **Google Cloud Run**

```bash
gcloud auth configure-docker
docker tag pdf-agent:latest gcr.io/<project-id>/pdf-agent:latest
docker push gcr.io/<project-id>/pdf-agent:latest
gcloud run deploy pdf-agent --image gcr.io/<project-id>/pdf-agent:latest --port 8501
```

#### **Docker Hub**

```bash
docker login
docker tag pdf-agent:latest <username>/pdf-agent:latest
docker push <username>/pdf-agent:latest
```

---

## Advanced Configuration

### Environment Variables

All configuration from `config.py` can be overridden via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | - | Groq API authentication key |
| `CHUNK_SIZE` | 800 | PDF chunk size in characters |
| `TOP_K` | 10 | Number of chunks to retrieve |
| `SIMILARITY_THRESHOLD` | 0.28 | Semantic similarity threshold |
| `LLM_MODEL` | llama-3.3-70b-versatile | LLM model to use |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARNING) |

### Volume Mounts

Three key volumes for data persistence:

- `/app/data/uploads` - Uploaded PDF files
- `/app/data/chroma_db` - Vector database (ChromaDB)
- `/app/data/logs` - Application logs

### Resource Limits

For production, limit resources:

```yaml
services:
  pdf-agent:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs pdf-agent

# Verify environment variables
docker-compose config
```

### Memory issues

The app requires ~2GB RAM minimum. Increase Docker's memory allocation:

- **Windows/Mac**: Docker Desktop Settings → Resources → Memory (set to 4GB+)
- **Linux**: No limit by default, but monitor with `docker stats`

### Groq API errors

- Verify `GROQ_API_KEY` is set correctly in `.env`
- Check API key at [Groq Console](https://console.groq.com/)
- Ensure you're within API rate limits

### Chroma DB persistence

If vector DB isn't persisting:

1. Verify volume mount: `docker-compose ps`
2. Check volume contents: `docker volume inspect pdf_agent_chroma_db`
3. Ensure write permissions: `docker-compose exec pdf-agent ls -la /app/data/chroma_db`

---

## Performance Optimization

### Image Size

Current image size: ~2.5GB (due to ML models)

To reduce:

```dockerfile
# In Dockerfile, use slim variants and remove unnecessary packages
RUN apt-get autoremove -y && apt-get clean
```

### Build Caching

Leverage Docker's layer caching:

```bash
# Separate requirements installation for better caching
docker build --progress=plain -t pdf-agent:latest .
```

### Multi-architecture builds

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t pdf-agent:latest .
```

---

## Security Best Practices

✅ **Implemented in Dockerfile:**
- Non-root user (`appuser`)
- Minimal base image (python:3.11-slim)
- No secrets in image
- Health checks enabled

✅ **Recommended additions:**
- Use Docker secrets for GROQ_API_KEY in Swarm
- Enable Docker content trust
- Scan images: `docker scan pdf-agent:latest`
- Use private registries for sensitive deployments

---

## Maintenance

### Update the application

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build --no-cache

# Restart service
docker-compose up -d
```

### Cleanup

```bash
# Remove all stopped containers
docker container prune

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune -a
```

---

## Next Steps

- [Kubernetes Deployment](./KUBERNETES.md) - Deploy to K8s clusters
- [CI/CD Integration](./CI_CD.md) - Automate builds and deployments
- [Monitoring](./MONITORING.md) - Setup logs, metrics, and alerts

For issues, refer to the [GitHub Issues](https://github.com/yourusername/pdf_agent/issues) page.
