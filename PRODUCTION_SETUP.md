# Production Deployment Guide

## Prerequisites

1. **Sync Content Folder** (Required - not in version control)
   ```bash
   # From your development machine, sync the private content folder
   # Create sync script (adjust paths and SSH config as needed):
   
   #!/bin/zsh
   # sync-content-server.sh
   SOURCE_DIR="/path/to/portfolio-ai-assistant/content/"
   REMOTE_HOST="yourserver"
   REMOTE_DIR="/path/to/production/portfolio-ai-assistant/"
   
   rsync -avz --progress "$SOURCE_DIR" "$REMOTE_HOST:$REMOTE_DIR"
   ```

2. **SSH Setup** (If using SSH keys)
   ```bash
   # Copy SSH keys from Windows to WSL (if needed)
   cp /mnt/c/Users/YourUser/.ssh/your_key ~/.ssh/
   chmod 600 ~/.ssh/your_key
   ```

## Quick Start

1. **Get Latest Code**
   ```bash
   git pull
   ```

2. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.prod.example .env.prod
   
   # Edit with your actual values
   nano .env.prod
   ```

3. **Sync Content** (First time and when content changes)
   ```bash
   # Run your content sync script
   ./sync-content-server.sh
   ```

4. **Build and Deploy Services**
   ```bash
   # Build backend (includes synced content)
   docker-compose -f docker-compose.prod.yml --env-file .env.prod build portfolio_backend_prod
   
   # Deploy the full stack
   docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

5. **Initialize Database** (First deployment only)
   ```bash
   # Copy required files to container (scripts and content are in root directory)
   docker cp ./scripts/ portfolio_backend_prod:/app/
   docker cp ./content/ portfolio_backend_prod:/app/
   docker cp ./noir-quotes.json portfolio_backend_prod:/app/
   
   # Run migrations
   docker exec portfolio_backend_prod alembic upgrade head
   
   # Load portfolio content (use hybrid for production)
   docker exec portfolio_backend_prod bash -c "cd /app && python -m scripts.ingest_portfolio_hybrid"
   
   # Load conversation quotes
   docker exec portfolio_backend_prod bash -c "cd /app && python -m scripts.load_quotes"
   ```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 shared_portainer_network                    │
├─────────────────┬─────────────────┬─────────────────────────┤
│    Frontend     │     Backend     │       Data Layer        │
│                 │                 │                        │
│  portfolio_     │  portfolio_     │  portfolio_postgres_    │
│  frontend_prod  │  backend_prod   │  prod (PostgreSQL +    │
│  (Astro Static) │  (FastAPI +     │  pgvector)             │
│  Port: 3000     │  Gunicorn +     │  Port: 5432            │
│                 │  Uvicorn)       │                        │
│                 │  Port: 8000     │  portfolio_redis_prod  │
│                 │                 │  (Redis Cache)         │
│                 │                 │  Port: 6379            │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## Container Communication

- **Frontend → Backend**: `http://portfolio_backend_prod:8000`
- **Backend → Database**: `postgresql+asyncpg://user:pass@portfolio_postgres_prod:5432/db`  
- **Backend → Redis**: `redis://portfolio_redis_prod:6379/0`

## Nginx Proxy Manager Setup

Point your domain to:
- **Frontend**: `http://portfolio_frontend_prod:3000`
- **Backend API**: `http://portfolio_backend_prod:8000` (if exposing API directly)

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_PASSWORD` | Database password | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | ✅ |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `CORS_ORIGINS` | Allowed frontend origins | ✅ |
| `AI_PROVIDER` | `openai` or `gemini` | Optional |
| `WORKERS` | Gunicorn worker count | Optional |

## Health Checks

All services include health checks:
- **Backend**: `GET /api/health`
- **Frontend**: HTTP 200 on port 3000
- **Database**: PostgreSQL connection test
- **Redis**: Redis ping test

## Data Persistence

- **PostgreSQL Data**: `postgres_data_prod` volume
- **Redis Data**: `redis_data_prod` volume

## Monitoring Commands

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f [service_name]

# Health check all services
docker-compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

## Scaling

Adjust worker count in `.env.prod`:
```bash
WORKERS=8  # Scale based on CPU cores
```

Then restart backend:
```bash
docker-compose -f docker-compose.prod.yml restart portfolio_backend_prod
```

## Content Management

### Updating Portfolio Content

When you update portfolio content on your development machine:

1. **Sync Content**:
```bash
./sync-content-server.sh
```

2. **Rebuild Backend** (to include new content):
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.prod build portfolio_backend_prod
docker-compose -f docker-compose.prod.yml --env-file .env.prod restart portfolio_backend_prod
```

3. **Copy Files and Re-ingest Content**:
```bash
# Copy updated files to container
docker cp ./scripts/ portfolio_backend_prod:/app/
docker cp ./content/ portfolio_backend_prod:/app/
docker cp ./noir-quotes.json portfolio_backend_prod:/app/

# Re-ingest content
docker exec portfolio_backend_prod bash -c "cd /app && python -m scripts.ingest_portfolio_hybrid"
```

### Content Folder Structure

The content folder contains private portfolio documentation:
- `projects/` - Detailed project descriptions and technical details
- `experience/` - Work history and career information  
- `personal/` - Background, preferences, and personal insights

**Note**: Content is intentionally excluded from version control to keep sensitive information private while allowing the codebase to remain public.