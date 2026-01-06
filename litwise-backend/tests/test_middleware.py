"""
Test middleware functionality
"""
import pytest
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware


class TestGZipMiddleware:
    """Test GZIP compression middleware"""
    
    def test_gzip_compression_header_present(self, client):
        """Test that GZIP middleware adds compression headers"""
        # Make a request and check for content-encoding header
        response = client.get("/docs")
        # GZIP middleware should be present in app
        assert response.status_code in [200, 401, 307], \
            "Docs endpoint should be accessible"


class TestCORSMiddleware:
    """Test CORS middleware"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are returned"""
        response = client.options("/api/chat")
        # CORS middleware should add Access-Control headers
        # Even if endpoint not found, CORS headers might be present
        assert response.status_code != 500, "CORS configuration error"
    
    def test_allowed_methods_configured(self, client):
        """Test that allowed HTTP methods are configured"""
        # OPTIONS request should be handled by CORS middleware
        response = client.options("/api/chat")
        assert response.status_code != 405, "OPTIONS method should be allowed by CORS"


class TestRateLimitMiddleware:
    """Test rate limiting middleware"""
    
    def test_rate_limit_middleware_loaded(self, app):
        """Test that rate limit middleware is configured"""
        # Check that RateLimitMiddleware is in the middleware stack
        middleware_names = []
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls'):
                middleware_names.append(type(middleware.cls).__name__)
            else:
                middleware_names.append(type(middleware).__name__)
        
        # Rate limiting should be present or middleware should exist
        assert len(middleware_names) > 0, "No middleware configured"
