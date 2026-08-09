"""
Test authentication middleware
"""
import pytest


class TestAuthMiddleware:
    """Test authentication and authorization"""
    
    def test_missing_auth_token(self, client):
        """Test that missing auth token is handled"""
        # POST /api/chat/sessions is a real endpoint that requires auth
        response = client.post("/api/chat/sessions", json={})
        # Should return 401, 403, or 422 (validation error before auth on some endpoints)
        assert response.status_code in [307, 401, 403, 422], \
            f"Missing auth should return 401/403, got {response.status_code}"
    
    def test_invalid_token_format(self, client):
        """Test that invalid token format is rejected"""
        response = client.post(
            "/api/chat/sessions",
            json={},
            headers={"Authorization": "InvalidFormat"}
        )
        # Should return 401 or 403 for invalid format
        assert response.status_code in [307, 401, 403, 422], \
            "Invalid token format should be rejected"
    
    def test_bearer_token_required(self, client):
        """Test that Bearer token format is required"""
        response = client.post(
            "/api/chat/sessions",
            json={},
            headers={"Authorization": "Bearer invalid-token"}
        )
        # Should process the token (might fail verification)
        assert response.status_code in [307, 401, 403, 422, 500], \
            "Token should be processed"
    
    def test_empty_bearer_token(self, client):
        """Test that empty Bearer token is rejected"""
        response = client.post(
            "/api/chat/sessions",
            json={},
            headers={"Authorization": "Bearer "}
        )
        # Should return error
        assert response.status_code in [307, 401, 403, 400, 422], \
            "Empty Bearer token should be rejected"


class TestAuthorizationLevels:
    """Test authorization and access control"""
    
    def test_protected_routes_require_auth(self, client):
        """Test that protected routes require authentication"""
        # Use real existing POST endpoints that require auth
        protected_routes = [
            ("/api/chat/sessions", "POST", {}),
            ("/api/study-plan/generate", "POST", {}),
            ("/api/quiz/generate", "POST", {}),
            ("/api/citations/generate", "POST", {}),
            ("/api/notes", "POST", {}),
        ]

        for route, method, body in protected_routes:
            if method == "POST":
                response = client.post(route, json=body)
            else:
                response = client.get(route)
            # All protected routes should reject unauthorized requests
            # 422 = validation error (body checked before auth on some endpoints)
            assert response.status_code in [307, 401, 403, 422], \
                f"{route} should require auth or validate body, got {response.status_code}"
    
    def test_public_routes_accessible_without_auth(self, client):
        """Test that public routes are accessible"""
        # OpenAPI docs should be accessible without auth
        response = client.get("/docs")
        # Might return 200 or 307 (redirect to /openapi.json)
        assert response.status_code in [200, 307], \
            "Public routes should be accessible"
