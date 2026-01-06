"""
Test API route availability and basic responses
"""
import pytest


class TestChatRoutes:
    """Test chat endpoints"""
    
    def test_chat_routes_registered(self, client):
        """Test that chat routes are registered"""
        # Test that the app responds to requests (even if no auth, we get a proper response)
        response = client.options("/api/chat")
        # Should not return 404
        assert response.status_code != 404, "Chat route not found"
    
    def test_missing_auth_returns_401_or_403(self, client):
        """Test that missing auth token returns proper error"""
        response = client.get("/api/chat")
        # Should return 401 (Unauthorized) or 403 (Forbidden), not 500
        assert response.status_code in [401, 403, 307], \
            f"Expected 401/403/307 for missing auth, got {response.status_code}"


class TestStudyPlanRoutes:
    """Test study plan endpoints"""
    
    def test_study_plan_routes_registered(self, client):
        """Test that study plan routes are registered"""
        response = client.options("/api/study-plan")
        assert response.status_code != 404, "Study plan route not found"


class TestCitationRoutes:
    """Test citation endpoints"""
    
    def test_citation_routes_registered(self, client):
        """Test that citation routes are registered"""
        response = client.options("/api/citations")
        assert response.status_code != 404, "Citation route not found"


class TestLiteratureReviewRoutes:
    """Test literature review endpoints"""
    
    def test_literature_review_routes_registered(self, client):
        """Test that literature review routes are registered"""
        response = client.options("/api/literature-review")
        assert response.status_code != 404, "Literature review route not found"


class TestQuizRoutes:
    """Test quiz endpoints"""
    
    def test_quiz_routes_registered(self, client):
        """Test that quiz routes are registered"""
        response = client.options("/api/quiz")
        assert response.status_code != 404, "Quiz route not found"


class TestExportRoutes:
    """Test export endpoints"""
    
    def test_export_routes_registered(self, client):
        """Test that export routes are registered"""
        response = client.options("/api/export")
        assert response.status_code != 404, "Export route not found"


class TestNotesRoutes:
    """Test notes endpoints"""
    
    def test_notes_routes_registered(self, client):
        """Test that notes routes are registered"""
        response = client.options("/api/notes")
        assert response.status_code != 404, "Notes route not found"
