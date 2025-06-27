# sbtl | Portfolio + AI Assistant

**Live Site**: [sbtl.dev](https://sbtl.dev)

An interactive portfolio website featuring a sophisticated AI assistant that provides personalized, context-aware responses about Steven's background, projects, and experience. This isn't just another chatbot—it's a full-featured conversational AI that remembers visitors (), understands context, and delivers responses with cinematic flair.

## What Makes This Special

**Advanced AI Integration**: Seamlessly switches between OpenAI and Google Gemini providers using atomic-agents framework, with intelligent query classification and adaptive response strategies. The system automatically detects whether you're asking about specific projects, seeking a broad overview, or just making conversation.

**Sophisticated Animations**: Features a production-grade GSAP animation system where text literally emerges from scattered particles, with race-condition protection and timing guarantees. Every response materializes with individual character animations that preserve link interactivity throughout.

**RAG-Powered Responses**: Implements Retrieval-Augmented Generation with PostgreSQL + pgvector for hybrid semantic and content-based search. The system intelligently expands queries using project metadata and retrieves nearby content chunks for comprehensive context assembly, ensuring responses are grounded in actual portfolio content.

## Future Features

**Privacy-First Memory**: Recognizes returning visitors without requiring any login or tracking, using browser fingerprinting and intelligent caching. The AI remembers previous conversations and builds visitor insights while maintaining complete privacy—all data is hashed and anonymized.

## Tech Stack

**Backend**: FastAPI with async SQLAlchemy, PostgreSQL + pgvector for RAG-based semantic search, Redis for caching, multi-provider AI integration with structured responses

**Frontend**: Astro 5.1 with React 19 islands, TypeScript throughout, GSAP for advanced animations, Tailwind CSS with custom responsive design

**AI Layer**: OpenAI API and Google Gemini with Instructor for type-safe responses, Atomic Agents framework, RAG implementation with vector embeddings for intelligent portfolio content retrieval

**Infrastructure**: Docker containerization with Gunicorn + Uvicorn workers, WebSocket real-time communication, automated database migrations with Alembic

## Deployment

This portfolio application is deployed on a self-hosted Kubernetes (K3s) cluster with the following architecture:

### Infrastructure
- **Container Orchestration**: Kubernetes (K3s)
- **Database**: PostgreSQL with pgvector extension for semantic search
- **Cache**: Redis for session management and caching
- **VPN**: All AI API calls are routed through a VPN for privacy
- **SSL/TLS**: Automated certificate management via Let's Encrypt

### CI/CD Pipeline
The application uses GitHub Actions for continuous deployment:
1. Push to `main` branch triggers the workflow
2. Docker images are built and pushed to Docker Hub
3. The K3s cluster automatically pulls and deploys the new images
4. Zero-downtime rolling deployments ensure the site stays available

### Deployment Configuration
Kubernetes manifests and deployment scripts are maintained in a separate private repository for security. The deployment includes:
- Automated database migrations
- Content ingestion for the AI assistant
- Health checks and auto-healing
- Horizontal scaling capabilities

### Domains
The application is accessible at [sbtl.dev](https://sbtl.dev) with automatic HTTPS redirection.

*Note: Deployment configurations and infrastructure details are not included in this repository.*

## Key Features

- **Intelligent Conversation**: RAG-powered context-aware responses using intelligent portfolio content retrieval
- **Mobile Optimization**: Device-aware response length and adaptive animation timing
- **Real-Time Communication**: WebSocket-based chat with message debouncing and rate limiting
- **Noir-Style Engagement**: 77+ curated conversation starters with film noir developer humor
- **Advanced Testing**: 1,270+ lines of comprehensive async test coverage with mocking strategies
- **Production Ready**: Health checks, monitoring, and containerized deployment with proper security

## The Experience

Visitors are greeted with atmospheric quotes that set a noir tone, then can engage in natural conversation about Steven's work. The AI draws from detailed project documentation, work history, and personal insights to provide nuanced responses. Whether you're a recruiter looking for specific technical details or just curious about the journey from live event operations to full-stack development, the assistant adapts its communication style accordingly.

The interface feels like a terminal session crossed with a magical typewriter—responses materialize letter by letter from scattered particles, creating an engaging visual experience that never gets in the way of the content.

Built as both a showcase of modern web development practices and a functional tool for portfolio exploration, this project demonstrates enterprise-level architecture patterns in an accessible, interactive format.
