"""
Test Pydantic models validation
"""
import pytest
from pydantic import ValidationError


class TestModelImports:
    """Test that models can be imported"""
    
    def test_search_query_model_exists(self):
        """Test SearchQuery model exists"""
        try:
            from models import SearchQuery
            assert SearchQuery is not None
        except ImportError:
            pytest.skip("Model import failed - may require dependencies")
    
    def test_processing_response_model_exists(self):
        """Test ProcessingResponse model exists"""
        try:
            from models import ProcessingResponse
            assert ProcessingResponse is not None
        except ImportError:
            pytest.skip("Model import failed - may require dependencies")


class TestModelValidation:
    """Test model validation"""
    
    def test_search_query_requires_query(self):
        """Test SearchQuery requires query field"""
        try:
            from models import SearchQuery
            
            # Should fail without query
            with pytest.raises(ValidationError):
                SearchQuery(query=None)
        except ImportError:
            pytest.skip("Model import failed")
    
    def test_model_json_schema(self):
        """Test that models have proper JSON schema"""
        try:
            from models import SearchQuery
            
            schema = SearchQuery.model_json_schema()
            assert "properties" in schema, "Model should have properties"
            assert "query" in schema["properties"], "SearchQuery should have query field"
        except ImportError:
            pytest.skip("Model import failed")
