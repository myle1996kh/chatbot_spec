"""FastAPI application initialization."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.utils.logging import configure_logging, get_logger

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


# Import and include routers (will be added in Phase 3)
# from src.api import chat, sessions
# from src.api.admin import agents, tools, tenants, monitoring
# app.include_router(chat.router, prefix="/api", tags=["chat"])
# app.include_router(sessions.router, prefix="/api", tags=["sessions"])
# app.include_router(agents.router, prefix="/api/admin", tags=["admin-agents"])
# app.include_router(tools.router, prefix="/api/admin", tags=["admin-tools"])
# app.include_router(tenants.router, prefix="/api/admin", tags=["admin-tenants"])
# app.include_router(monitoring.router, prefix="/api/admin", tags=["admin-monitoring"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
