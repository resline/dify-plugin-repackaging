from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api import websocket
from app.api.v1.endpoints import marketplace as v1_marketplace
from app.api.v1.endpoints import tasks as v1_tasks
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(websocket.router)

# V1 endpoints
app.include_router(v1_marketplace.router, prefix=settings.API_V1_STR)
app.include_router(v1_tasks.router, prefix=settings.API_V1_STR)

# Create necessary directories
os.makedirs(settings.TEMP_DIR, exist_ok=True)


@app.get("/")
def read_root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        from app.workers.celery_app import redis_client
        redis_client.ping()
        
        return {
            "status": "healthy",
            "redis": "connected",
            "version": settings.APP_VERSION
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)