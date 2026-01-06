"""
Rate Limiting Service for LitWise API
Implements user-based and endpoint-based rate limiting using Redis
"""

import redis
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
from dotenv import load_dotenv
from fastapi import HTTPException, Request, Depends
from auth_middleware import get_current_user, AuthUser

load_dotenv()


# Redis configuration using Upstash
REDIS_URL = os.getenv("REDIS_URL")
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")


class RateLimiterService:
    """
    Rate limiting service using Redis with support for:
    - User-based rate limiting (primary)
    - Endpoint-based rate limiting
    - Custom limits per endpoint
    - Grace periods for fair usage
    """

    def __init__(self):
        """Initialize Redis connection from Upstash configuration."""
        try:
            # Try standard Redis URL first (for local Redis)
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            print("✅ Connected to Redis (Standard URL)")
        except Exception as e:
            print(f"❌ Error connecting to Redis (Standard URL): {e}")
            try:
                # Fallback to HTTP REST API (Upstash REST)
                import requests

                self.use_rest_api = True
                self.rest_url = UPSTASH_REDIS_REST_URL
                self.rest_token = UPSTASH_REDIS_REST_TOKEN
                print("✅ Connected to Redis (Upstash REST API)")
            except Exception as e:
                print(f"❌ Error connecting to Redis (Upstash REST API): {e}")
                raise ConnectionError("Failed to connect to Redis using both methods.")

    def _get_key(self, user_id: str, endpoint: str, window_type: str = "minute") -> str:
        """Generate Redis key for rate limiting"""
        return f"ratelimit:{user_id}:{endpoint}:{window_type}:{self._get_window_time(window_type)}"

    @staticmethod
    def _get_window_time(window_type: str = "minute") -> str:
        """Get current window time for grouping requests"""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if window_type == "minute":
            return now.strftime("%Y%m%d%H%M")
        elif window_type == "hour":
            return now.strftime("%Y%m%d%H")
        elif window_type == "day":
            return now.strftime("%Y%m%d")
        return now.strftime("%Y%m%d%H%M")

    def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        max_requests: int = 100,
        window_seconds: int = 60,
        endpoint_name: Optional[str] = None,
    ) -> Dict:
        """
        Check if user has exceeded rate limit for endpoint

        Args:
            user_id: Authenticated user ID
            endpoint: API endpoint path
            max_requests: Max requests allowed
            window_seconds: Time window in seconds
            endpoint_name: Human-readable endpoint name for logging

        Returns:
            {
                'allowed': bool,
                'remaining': int,
                'reset_in': int (seconds),
                'limit': int
            }
        """
        if not self.redis_client and not hasattr(self, "use_rest_api"):
            return {
                "allowed": True,
                "remaining": -1,
            }  # No rate limiting if Redis is not connected

        window_type = self._get_window_type(window_seconds)
        key = self._get_key(user_id, endpoint, window_type)

        try:
            # Get current count
            current = self.redis_client.get(key)
            current_count = int(current) if current else 0

            if current_count >= max_requests:
                ttl = self.redis_client.ttl(key)
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_in": ttl if ttl > 0 else window_seconds,
                    "limit": max_requests,
                    "endpoint": endpoint_name or endpoint,
                }

            # Increment count
            new_count = self.redis_client.incr(key)

            # Set expiration if first request
            if new_count == 1:
                self.redis_client.expire(key, window_seconds)

            return {
                "allowed": True,
                "remaining": max_requests - new_count,
                "reset_in": self.redis_client.ttl(key),
                "limit": max_requests,
                "current": new_count,
            }

        except Exception as e:
            print(f"❌ Error in rate limiting {user_id}: {e}")
            return {"allowed": True, "remaining": -1}  # Fail open on error

    @staticmethod
    def _get_window_type(window_seconds: int) -> str:
        """Determine window type based on seconds"""
        if window_seconds <= 60:
            return "minute"
        elif window_seconds <= 3600:
            return "hour"
        else:
            return "day"

    def reset_user_limit(self, user_id: str, endpoint: str):
        """Reset rate limit for user (admin function)"""
        pattern = f"ratelimit:{user_id}:{endpoint}:*"
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                print(f"✅ Reset rate limit for {user_id} on {endpoint}")
        except Exception as e:
            print(f"❌ Failed to reset rate limit: {e}")


# Global instance
rate_limiter = RateLimiterService()


# Rate limit configurations by endpoint
RATE_LIMITS = {
    # Chat operations - expensive LLM calls
    "/api/chat/stream": {
        "max_requests": 20,
        "window_seconds": 60,
        "description": "Chat streaming requests"
    },
    "/api/chat/sessions": {
        "max_requests": 50,
        "window_seconds": 60,
        "description": "Chat session creation"
    },
    
    # Quiz operations - AI intensive
    "/api/quiz/generate": {
        "max_requests": 5,
        "window_seconds": 3600,  # 1 hour
        "description": "Quiz generation"
    },
    "/api/quiz/attempt/submit": {
        "max_requests": 100,
        "window_seconds": 3600,
        "description": "Quiz submission"
    },
    
    # Citation operations
    "/api/citations/generate": {
        "max_requests": 15,
        "window_seconds": 3600,
        "description": "Citation generation"
    },
    "/api/citations/extract": {
        "max_requests": 10,
        "window_seconds": 3600,
        "description": "Citation extraction"
    },
    "/api/ai-citations/generate": {
        "max_requests": 15,
        "window_seconds": 3600,
        "description": "AI citation generation"
    },
    
    # Study plan - most intensive
    "/api/study-plan/generate": {
        "max_requests": 3,
        "window_seconds": 86400,  # 1 day
        "description": "Study plan generation"
    },
    
    # Literature review
    "/api/literature-review/generate": {
        "max_requests": 5,
        "window_seconds": 3600,
        "description": "Literature review generation"
    },
    
    # General API limit (fallback)
    "default": {
        "max_requests": 100,
        "window_seconds": 60,
        "description": "General API requests"
    }
}

async def rate_limit_dependency(
    request: Request,
    current_user: AuthUser = Depends(get_current_user)
) -> Dict:
    """
    FastAPI dependency for rate limiting
    Add this to route dependencies to enforce rate limiting
    
    Usage in routes:
        @router.post("/endpoint")
        async def my_endpoint(
            rate_limit_check: Dict = Depends(rate_limit_dependency)
        ):
            if not rate_limit_check['allowed']:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {rate_limit_check['reset_in']} seconds"
                )
    """
    endpoint = request.url.path
    method = request.method
    full_endpoint = f"{method}:{endpoint}"
    
    # Get rate limit config for this endpoint
    limit_config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    
    # Check rate limit
    result = rate_limiter.check_rate_limit(
        user_id=current_user.id,
        endpoint=full_endpoint,
        max_requests=limit_config["max_requests"],
        window_seconds=limit_config["window_seconds"],
        endpoint_name=limit_config["description"]
    )
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Rate limit exceeded for {limit_config['description']}",
                "reset_in_seconds": result["reset_in"],
                "limit": result["limit"],
                "retry_after": result["reset_in"]
            },
            headers={"Retry-After": str(result["reset_in"])}
        )
    return result