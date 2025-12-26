# sbtl.dev | Portfolio

**Live Site**: [sbtl.dev](https://sbtl.dev)

My portfolio site with an AI assistant you can chat with to learn about my background, projects, and experience. Instead of scrolling through static pages, you can just ask questions - it uses RAG to pull relevant info from my project docs and work history.

## How It Works

The AI assistant uses vector embeddings (pgvector) to find relevant content chunks from my portfolio data, then feeds that context to OpenAI/Gemini to generate responses. Responses stream in with a character animation effect.

## Tech Stack

**Frontend**: Astro 5.1, React 19, TypeScript, GSAP, Tailwind CSS

**Backend**: FastAPI, async SQLAlchemy, PostgreSQL + pgvector, Redis

**AI**: OpenAI/Gemini APIs, Instructor for typed responses, Atomic Agents framework

**Infrastructure**: Self-hosted K3s cluster, Docker, GitHub Actions CI/CD, automated SSL via Let's Encrypt

## Deployment

Runs on my bare metal K3s cluster with:
- PostgreSQL + pgvector for semantic search
- Redis for caching
- GitHub Actions for CI/CD (push to main triggers build and deploy)
- Zero-downtime rolling deployments

Deployment configs are in a separate private repo.

## Local Development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Requires `.env` with API keys for OpenAI/Gemini.
