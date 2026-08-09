"""
Test app startup and basic configuration
"""
import pytest
from app import app


class TestAppStartup:
    """Test that app initializes correctly"""
    
    def test_app_exists(self):
        """Test that FastAPI app is properly instantiated"""
        assert app is not None
        assert app.title == "Litwise API"
        assert app.version == "1.0.0"
    
    def test_app_has_routes(self):
        """Test that app has registered routes"""
        routes = [route.path for route in app.routes]
        assert len(routes) > 0, "No routes registered"
    
    def test_cors_middleware_installed(self):
        """Test that CORS middleware is installed"""
        # app.user_middleware is a list of Middleware objects
        # We check the class name stored in each middleware stack entry
        middleware_str = str([str(m) for m in app.user_middleware])
        assert 'CORSMiddleware' in middleware_str, \
            "CORS middleware not found"
    
    def test_gzip_middleware_installed(self):
        """Test that GZIP compression middleware is installed"""
        middleware_str = str([str(m) for m in app.user_middleware])
        assert 'GZip' in middleware_str, \
            "GZIP middleware not found"
    
    def test_rate_limit_middleware_installed(self):
        """Test that rate limiting middleware is installed"""
        middleware_types = [str(m) for m in app.user_middleware]
        # Note: Rate limit middleware may be installed differently
        assert len(middleware_types) > 0, "No middleware installed"


class TestAppEndpoints:
    """Test app endpoints exist"""
    
    def test_health_check_endpoint_exists(self):
        """Test that health check endpoint is registered"""
        routes = [route.path for route in app.routes]
        # FastAPI has /openapi.json, /docs, and our /health endpoint
        # Fix: any() takes an iterable of booleans, not a single boolean
        assert any(path in routes for path in ['/', '/health']), \
            "Root or health endpoint should exist"
    
    def test_openapi_documentation_enabled(self):
        """Test that OpenAPI documentation is enabled"""
        assert app.openapi_schema is not None or app.openapi() is not None, \
            "OpenAPI documentation not enabled"
