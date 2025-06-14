# Production Deployment Guide

## Quick Start

1. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.prod.example .env.prod
   
   # Edit with your actual values
   nano .env.prod
   ```

2. **Deploy Services**
   ```bash
   # Deploy the full stack
   docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

3. **Initialize Database** (First deployment only)
   ```bash
   # Run migrations
   docker exec portfolio_backend_prod alembic upgrade head
   
   # Load portfolio content
   docker exec portfolio_backend_prod python scripts/reingest_all.py
   
   # Load conversation quotes
   docker exec portfolio_backend_prod python scripts/load_quotes.py
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