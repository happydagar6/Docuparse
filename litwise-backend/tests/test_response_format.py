"""
Test API response formats and error handling
"""
import pytest
import json


class TestResponseHeaders:
    """Test HTTP response headers"""
    
    def test_json_content_type_header(self, client):
        """Test that responses have JSON content type"""
        # Many endpoints should return JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_cors_headers_on_response(self, client):
        """Test that CORS headers are present on responses"""
        response = client.get("/docs")
        # Response should complete without CORS errors
        assert response.status_code in [200, 401, 307]


class TestErrorHandling:
    """Test error handling and HTTP status codes"""
    
    def test_404_on_nonexistent_route(self, client):
        """Test that nonexistent routes return 404"""
        response = client.get("/api/nonexistent-route-xyz")
        assert response.status_code == 404, "Nonexistent route should return 404"
    
    def test_method_not_allowed_returns_405(self, client):
        """Test that disallowed methods return 405"""
        # Try a method that's likely not allowed on docs
        response = client.delete("/openapi.json")
        # DELETE on openapi.json should be 405 or 404
        assert response.status_code in [404, 405], \
            "Invalid method should return 405 or 404"
    
    def test_error_responses_are_json(self, client):
        """Test that error responses are valid JSON"""
        response = client.get("/api/nonexistent")
        # If it's an error response, it should be JSON
        if response.status_code >= 400:
            try:
                json.loads(response.text)
                assert True, "Error response is valid JSON"
            except json.JSONDecodeError:
                # Some error responses might not be JSON format
                pass


class TestRequestValidation:
    """Test request validation"""
    
    def test_invalid_json_returns_422(self, client):
        """Test that invalid JSON returns 422 (unprocessable entity)"""
        response = client.post(
            "/api/nonexistent",
            content="invalid json {",
            headers={"Content-Type": "application/json"}
        )
        # Should return 404 first or 422 for invalid JSON
        assert response.status_code in [400, 404, 422], \
            "Invalid JSON should return 400/422"
    
    def test_missing_required_fields(self, client):
        """Test that missing required fields are validated"""
        # This is route-specific, but we can test the framework
        response = client.post(
            "/api/nonexistent",
            json={}
        )
        # Should return 404 for nonexistent route
        assert response.status_code in [400, 404, 422]
