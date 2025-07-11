from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.middleware import JSONResponseMiddleware, ErrorHandlingMiddleware, RequestValidationMiddleware
from app.api import websocket
from app.api.v1.endpoints import marketplace as v1_marketplace
from app.api.v1.endpoints import tasks as v1_tasks
from app.api.v1.endpoints import files as v1_files
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging
import os

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set httpx logging to INFO level for better debugging
logging.getLogger("httpx").setLevel(logging.INFO)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add rate limiter to app state
app.state.limiter = limiter

# Add rate limit error handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add SlowAPI middleware
app.add_middleware(SlowAPIMiddleware)

# Add custom middleware for JSON responses and error handling
app.add_middleware(JSONResponseMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestValidationMiddleware)

# Set up CORS - should be added last to work properly
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
app.include_router(v1_files.router, prefix=settings.API_V1_STR)

# Directory creation moved to startup event to avoid permission issues during import


@app.on_event("startup")
async def startup_event():
    """Create necessary directories on startup"""
    try:
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        logger.info(f"Created temp directory: {settings.TEMP_DIR}")
    except Exception as e:
        logger.warning(f"Could not create temp directory {settings.TEMP_DIR}: {e}")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their processing time"""
    import time
    start_time = time.time()
    
    # Log request details
    logger = logging.getLogger(__name__)
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response details
        logger.info(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Time: {process_time:.3f}s"
        )
        raise


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