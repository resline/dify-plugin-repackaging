from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class JSONResponseMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure all API responses are properly formatted as JSON
    with correct Content-Type headers
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process the request
        response = await call_next(request)
        
        # Only process API endpoints
        if request.url.path.startswith("/api/"):
            # Check if response has a body
            if hasattr(response, "body_iterator"):
                # Read the response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                try:
                    # Try to parse as JSON to ensure it's valid
                    if body:
                        decoded_body = body.decode()
                        
                        # Check if it's HTML (common error response)
                        if decoded_body.strip().startswith(('<!DOCTYPE', '<html', '<?xml')):
                            logger.warning(f"Received HTML response for API endpoint {request.url.path}")
                            return JSONResponse(
                                content={
                                    "error": "Invalid response format",
                                    "detail": "API returned HTML instead of JSON. This usually indicates an error or API change.",
                                    "path": str(request.url.path),
                                    "timestamp": datetime.utcnow().isoformat()
                                },
                                status_code=502  # Bad Gateway
                            )
                        
                        json_data = json.loads(decoded_body)
                        
                        # Create new response with proper headers
                        return JSONResponse(
                            content=json_data,
                            status_code=response.status_code,
                            headers=dict(response.headers)
                        )
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response for {request.url.path}: {e}")
                    logger.error(f"Response body: {body[:500]}...")  # Log first 500 chars
                    logger.error(f"Response content-type: {response.headers.get('content-type', 'Not set')}")
                    
                    # Return error response
                    return JSONResponse(
                        content={
                            "error": "Internal server error",
                            "detail": "Invalid response format",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        status_code=500
                    )
                except Exception as e:
                    logger.error(f"Error processing response for {request.url.path}: {e}")
                    
                    return JSONResponse(
                        content={
                            "error": "Internal server error",
                            "detail": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        status_code=500
                    )
            
            # Ensure Content-Type is set for API responses
            if "content-type" not in response.headers:
                response.headers["content-type"] = "application/json"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and properly format all errors as JSON responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception(f"Unhandled exception for {request.url.path}")
            
            # Return properly formatted error response
            return JSONResponse(
                content={
                    "error": "Internal server error",
                    "detail": str(e),
                    "path": str(request.url.path),
                    "method": request.method,
                    "timestamp": datetime.utcnow().isoformat()
                },
                status_code=500,
                headers={"content-type": "application/json"}
            )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate incoming requests and add request ID for tracking
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracking
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log incoming request
        logger.info(f"[{request_id}] {request.method} {request.url.path}")
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response