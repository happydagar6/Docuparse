"""
Rate Limiting Middleware for FastAPI
Provides global rate limiting for all endpoints
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime
import logging
from services.rate_limiter_service import rate_limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global middleware for rate limiting
    Applies rate limits to all endpoints without explicit dependency injection
    """
    
    # [LITWISE RAG LOGIC]: The Whitelist (Exemptions)
    # Why we do this: If we blindly rate-limit everything, a user who refreshes the homepage 
    # too fast might get locked out of their own account (because the login route gets blocked).
    # We explicitly exempt Auth and Health Check endpoints so users can always log in and the 
    # AWS Load Balancer can always verify the server is alive.
    EXEMPT_ENDPOINTS = {
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
    }
    
    async def dispatch(self, request: Request, call_next):
        """
        [LITWISE RAG LOGIC]: The Global Interceptor
        Why we do this: Instead of manually adding rate-limiting code to all 50+ API endpoints,
        we use a FastAPI BaseHTTPMiddleware. This acts as a global 'security guard'. 
        Every single HTTP request must pass through this function before it is allowed to touch 
        the actual application code.
        """
        
        # Skip rate limiting for exempt endpoints
        if request.url.path in self.EXEMPT_ENDPOINTS:
            return await call_next(request)
        
        # Skip rate limiting for GET requests to list endpoints (read-only)
        if request.method == "GET" and "/list" in request.url.path:
            # More generous limit for read operations
            limit_config = RATE_LIMITS.get(request.url.path)
            if limit_config and "list" in request.url.path.lower():
                # Allow higher rate for list/read operations
                limit_config = {
                    "max_requests": 200,
                    "window_seconds": 60,
                    "description": "List/Read operations"
                }
                
        try:
            # Extract user ID from request (if authenticated)
            user_id = self._extract_user_id(request)
            
            # If not authenticated, allow to continue (will be checked by route dependencies)
            if not user_id:
                return await call_next(request)
            
            # Get rate limit config for this endpoint
            endpoint = request.url.path
            method = request.method
            full_endpoint = f"{method}:{endpoint}"
            
            limit_config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
            
            # Check rate limit
            check_result = rate_limiter.check_rate_limit(
                user_id=user_id,
                endpoint=full_endpoint,
                max_requests=limit_config["max_requests"],
                window_seconds=limit_config["window_seconds"],
                endpoint_name=limit_config["description"]
            )
            
            # [LITWISE RAG LOGIC]: The 429 Response
            # Why we do this: If the Redis counter exceeds the limit, we MUST return a 429 status code.
            # Crucially, we include the 'Retry-After' header. This tells the Frontend React app exactly
            # how many seconds it needs to pause before it is allowed to send the next request.
            if not check_result["allowed"]:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on endpoint {endpoint}"
                    f"Limit: {check_result['limit']}, Retry after: {check_result['reset_in']} seconds"
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Rate limit exceeded. Try again in {check_result['reset_in']} seconds",
                        "limit": check_result['limit'],
                        "reset_in_seconds": check_result['reset_in'],
                        "endpoint": limit_config["description"]
                    },
                    headers={
                        "Retry-After": str(check_result["reset_in"]),
                        "X-RateLimit-Limit": str(check_result["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                    }
                )
                
            # Add rate limit headers to response
            response = await call_next(request)
            from datetime import timezone
            response.headers["X-RateLimit-Limit"] = str(check_result['limit'])
            response.headers["X-RateLimit-Remaining"] = str(check_result['remaining'])
            response.headers["X-RateLimit-Reset"] = str(
                datetime.now(timezone.utc).timestamp() + check_result['reset_in']
            )
            return response
        
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Fail open - allow request if rate limiter has issues
            return await call_next(request)
        
    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        """Extract user ID from Authorization header"""
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # Token is JWT - would be validated by route dependency
                # For middleware, we just need to identify unique user
                # Use first 20 chars of token as user identifier
                token = auth_header[7:]
                return f"user_{hash(token) % 10000}" # Simple hash-based user ID
            return None
        except Exception as e:
            logger.error(f"Error extracting user ID from request: {e}")
            return None