"""
Test authentication middleware
"""
import pytest


class TestAuthMiddleware:
    """Test authentication and authorization"""
    
    def test_missing_auth_token(self, client):
        """Test that missing auth token is handled"""
        response = client.get("/api/chat")
        # Should return 401, 403, or redirect
        assert response.status_code in [307, 401, 403], \
            f"Missing auth should return 401/403, got {response.status_code}"
    
    def test_invalid_token_format(self, client):
        """Test that invalid token format is rejected"""
        response = client.get(
            "/api/chat",
            headers={"Authorization": "InvalidFormat"}
        )
        # Should return 401 or 403 for invalid format
        assert response.status_code in [307, 401, 403], \
            "Invalid token format should be rejected"
    
    def test_bearer_token_required(self, client):
        """Test that Bearer token format is required"""
        response = client.get(
            "/api/chat",
            headers={"Authorization": "Bearer invalid-token"}
        )
        # Should process the token (might fail verification)
        assert response.status_code in [307, 401, 403, 500], \
            "Token should be processed"
    
    def test_empty_bearer_token(self, client):
        """Test that empty Bearer token is rejected"""
        response = client.get(
            "/api/chat",
            headers={"Authorization": "Bearer "}
        )
        # Should return error
        assert response.status_code in [307, 401, 403, 400], \
            "Empty Bearer token should be rejected"


class TestAuthorizationLevels:
    """Test authorization and access control"""
    
    def test_protected_routes_require_auth(self, client):
        """Test that protected routes require authentication"""
        protected_routes = [
            "/api/chat",
            "/api/study-plan",
            "/api/quiz",
            "/api/citations",
            "/api/notes"
        ]
        
        for route in protected_routes:
            response = client.get(route)
            # All protected routes should reject unauthorized requests
            assert response.status_code in [307, 401, 403], \
                f"{route} should require auth, got {response.status_code}"
    
    def test_public_routes_accessible_without_auth(self, client):
        """Test that public routes are accessible"""
        # OpenAPI docs should be accessible without auth
        response = client.get("/docs")
        # Might return 200 or 307 (redirect to /openapi.json)
        assert response.status_code in [200, 307], \
            "Public routes should be accessible"
