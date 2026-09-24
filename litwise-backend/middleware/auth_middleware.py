"""
Authentication Middleware for FastAPI
Handles JWT token validation and user extraction from Supabase Auth tokens
"""

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
from dotenv import load_dotenv
load_dotenv()

# Security schemes
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

class AuthUser:
    """Represents an authenticated user"""
    def __init__(self, user_id: str, email: str = "", metadata: Optional[dict] = None):
        self.id = user_id
        self.email = email
        self.metadata = metadata or {}
        
    def __str__(self):
        return f"User(id={self.id}, email={self.email})"


def get_supabase_jwt_secret():
    """
    Get the JWT secret from Supabase
    This is the secret used to verify JWT tokens
    """
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_JWT_SECRET environment variable not set"
        )
    return SUPABASE_JWT_SECRET


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verify the JWT token from the Authorization header
    Returns the decoded token payload
    """
    try:
        token = credentials.credentials
        jwt_secret = get_supabase_jwt_secret()
        
        # This is our Stateless JWT Authentication.
        # Instead of doing a database lookup to see if the user is logged in,
        # we decode the token using the secret. If the signature matches, the token
        # is valid and hasn't been tampered with. This is highly scalable.
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True}
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token audience"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> AuthUser:
    """
    Get the current authenticated user from the JWT token
    This is the main dependency to use in protected routes
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.id, "email": user.email}
    """
    payload = await verify_token(credentials)
    
    # Extract user information from the JWT payload
    user_id = payload.get("sub")
    email = str(payload.get("email") or "")
    user_metadata = payload.get("user_metadata", {})
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token: user ID not found"
        )
    
    return AuthUser(
        user_id=user_id,
        email=email,
        metadata=user_metadata
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security)
) -> Optional[AuthUser]:
    """
    Get the current user if authenticated, otherwise return None
    Useful for endpoints that work both with and without authentication
    
    Usage:
        @app.get("/optional-auth")
        async def optional_route(user: Optional[AuthUser] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous user"}
    """
    if not credentials:
        return None
    
    try:
        payload = await verify_token(credentials)
        
        user_id = payload.get("sub")
        email = str(payload.get("email") or "")
        user_metadata = payload.get("user_metadata", {})
        
        if not user_id:
            return None
        
        return AuthUser(
            user_id=user_id,
            email=email,
            metadata=user_metadata
        )
    except HTTPException:
        # If token is invalid, just return None instead of raising error
        return None


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """
    Require admin privileges
    Check if user has admin role in their metadata
    
    Usage:
        @app.get("/admin")
        async def admin_route(user: AuthUser = Depends(require_admin)):
            return {"message": "Admin access granted"}
    """
    is_admin = user.metadata.get("is_admin", False)
    
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    return user
