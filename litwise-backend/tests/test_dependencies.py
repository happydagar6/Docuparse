"""
Test that required dependencies are available
"""
import pytest


class TestDependencyImports:
    """Test that critical dependencies are installed"""
    
    def test_fastapi_imported(self):
        """Test FastAPI is installed"""
        import fastapi
        assert fastapi.__version__
        assert "0.121" in fastapi.__version__ or "0.12" in fastapi.__version__
    
    def test_supabase_imported(self):
        """Test Supabase client is installed"""
        import supabase
        assert supabase is not None
    
    def test_redis_imported(self):
        """Test Redis client is installed"""
        import redis
        assert redis is not None
    
    def test_jwt_imported(self):
        """Test PyJWT is installed"""
        import jwt
        assert jwt is not None
    
    def test_langchain_imported(self):
        """Test LangChain is installed"""
        import langchain
        assert langchain is not None
    
    def test_openai_imported(self):
        """Test OpenAI is installed"""
        import openai
        assert openai is not None
    
    def test_sqlalchemy_imported(self):
        """Test SQLAlchemy is installed"""
        import sqlalchemy
        assert sqlalchemy is not None
    
    def test_pydantic_imported(self):
        """Test Pydantic is installed"""
        import pydantic
        assert pydantic is not None


class TestDependencyVersions:
    """Test that dependencies have correct versions"""
    
    def test_fastapi_version(self):
        """Test FastAPI version is appropriate"""
        import fastapi
        version = fastapi.__version__
        # Should be 0.121.x
        assert version.startswith("0.12"), f"FastAPI version {version} is acceptable"
    
    def test_pydantic_version(self):
        """Test Pydantic version is V2"""
        import pydantic
        version = pydantic.__version__
        # Should be 2.x
        assert version.startswith("2."), f"Pydantic V2 required, got {version}"
