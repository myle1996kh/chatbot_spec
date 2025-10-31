"""FastAPI application initialization."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.utils.logging import configure_logging, get_logger

# Import ALL models to ensure SQLAlchemy relationships are properly registered
# This must be done before any database operations
# These imports appear "unused" but are required for SQLAlchemy relationship resolution
from src.models.tenant import Tenant  # noqa: F401
from src.models.session import ChatSession  # noqa: F401
from src.models.message import Message  # noqa: F401
from src.models.llm_model import LLMModel  # noqa: F401
from src.models.tenant_llm_config import TenantLLMConfig  # noqa: F401
from src.models.base_tool import BaseTool  # noqa: F401
from src.models.output_format import OutputFormat  # noqa: F401
from src.models.tool import ToolConfig  # noqa: F401
from src.models.agent import AgentConfig, AgentTools  # noqa: F401
from src.models.permissions import TenantAgentPermission, TenantToolPermission  # noqa: F401

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AgentHub Multi-Agent Chatbot Framework",
    description="Production-ready multi-tenant chatbot framework using LangChain 0.3+",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        api_host=settings.API_HOST,
        api_port=settings.API_PORT,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("application_shutdown")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AgentHub Multi-Agent Chatbot Framework",
        "version": "0.1.0",
        "docs": "/docs"
    }


# Import and include routers
from src.api import chat, sessions

# Chat and session management endpoints (Phase 3)
app.include_router(chat.router, tags=["chat"])
app.include_router(sessions.router, tags=["sessions"])

# Admin endpoints (Phase 4 & Phase 8)
from src.api.admin import agents, tools, tenants, knowledge

app.include_router(agents.router, tags=["admin-agents"])
app.include_router(tools.router, tags=["admin-tools"])
app.include_router(tenants.router, tags=["admin-tenants"])
app.include_router(knowledge.router, tags=["admin-knowledge"])

# Monitoring endpoints (will be added in Phase 11)
# from src.api.admin import monitoring
# app.include_router(monitoring.router, tags=["admin-monitoring"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
