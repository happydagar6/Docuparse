"""
Redis Message Cache Service for LitWise
Provides efficient caching of chat messages to reduce database queries
and improve response times for message pagination.

Features:
- Cache paginated message results from database
- Auto-expiring cache with TTL (24 hours default)
- Per-session cache limits to prevent memory bloat
- Cache hit/miss tracking for performance monitoring
- Easy invalidation and cache clearing
"""

import json
import redis
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# Cache configuration
CACHE_TTL_HOURS = 24  # Messages expire after 24 hours
CACHE_TTL_SECONDS = CACHE_TTL_HOURS * 3600
MAX_MESSAGES_PER_SESSION = 5000  # Limit cache size per session
CACHE_KEY_PREFIX = "messages"


class MessageCacheService:
    """
    Redis-based cache service for chat messages.
    
    Implements a production-ready caching layer that:
    - Reduces database queries by caching paginated results
    - Automatically expires old caches after TTL
    - Tracks cache performance metrics
    - Handles Redis connection failures gracefully
    """

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = None
        self.use_rest_api = False
        self._initialize_redis()

    def _initialize_redis(self) -> None:
        """Initialize Redis connection with fallback to REST API."""
        try:
            # Try standard Redis URL first (works for local Redis and Upstash direct connection)
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Message Cache: Connected to Redis (Standard URL)")
        except Exception as e:
            logger.warning(f"⚠️ Message Cache: Standard Redis connection failed: {e}")
            try:
                # Fallback to REST API (useful if only REST access is available)
                import requests
                self.use_rest_api = True
                self.rest_url = UPSTASH_REDIS_REST_URL
                self.rest_token = UPSTASH_REDIS_REST_TOKEN
                
                # Test REST connection
                response = requests.get(
                    f"{self.rest_url}/ping",
                    headers={"Authorization": f"Bearer {self.rest_token}"}
                )
                if response.status_code == 200:
                    logger.info("✅ Message Cache: Connected to Redis (Upstash REST API)")
                else:
                    raise ConnectionError(f"REST API ping failed: {response.status_code}")
            except Exception as rest_error:
                logger.error(f"❌ Message Cache: Failed to connect using both methods: {rest_error}")
                # Continue without cache - read-through pattern
                self.redis_client = None

    def _generate_cache_key(
        self,
        session_id: str,
        limit: int,
        cursor: Optional[str] = None,
        direction: str = "before"
    ) -> str:
        """
        Generate a Redis cache key for paginated messages.
        
        Args:
            session_id: Chat session ID
            limit: Number of messages per page
            cursor: Pagination cursor (optional)
            direction: Pagination direction (before/after)
            
        Returns:
            Cache key string
        """
        cursor_part = f":{cursor[:20]}" if cursor else ":none"
        return f"{CACHE_KEY_PREFIX}:{session_id}:{limit}:{direction}{cursor_part}"

    def _get_session_cache_key(self, session_id: str) -> str:
        """Generate cache key for session metadata (for tracking size)."""
        return f"{CACHE_KEY_PREFIX}:{session_id}:size"

    def get(
        self,
        session_id: str,
        limit: int,
        cursor: Optional[str] = None,
        direction: str = "before"
    ) -> Optional[Dict]:
        """
        Get cached paginated messages from Redis.
        
        Args:
            session_id: Chat session ID
            limit: Messages per page
            cursor: Pagination cursor
            direction: Pagination direction
            
        Returns:
            Cached message data or None if not found
        """
        if not self.redis_client:
            logger.warning("Redis client not available - cache disabled")
            return None

        try:
            cache_key = self._generate_cache_key(session_id, limit, cursor, direction)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.info(f"✅ Cache HIT: {cache_key}")
                return json.loads(cached_data)
            
            logger.info(f"⚠️  Cache MISS: {cache_key}")
            return None

        except Exception as e:
            logger.warning(f"❌ Error retrieving from cache: {e}")
            # Graceful degradation - return None and let caller fetch from DB
            return None

    def _serialize_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Convert datetime objects in messages to ISO format strings.
        Required for JSON serialization to Redis.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List with datetime objects converted to strings
        """
        serialized = []
        for msg in messages:
            serialized_msg = {}
            for key, value in msg.items():
                if isinstance(value, datetime):
                    # Convert datetime to ISO format string
                    serialized_msg[key] = value.isoformat()
                else:
                    serialized_msg[key] = value
            serialized.append(serialized_msg)
        return serialized

    def set(
        self,
        session_id: str,
        limit: int,
        messages: List[Dict],
        next_cursor: Optional[str],
        total_count: int,
        has_more: bool,
        cursor: Optional[str] = None,
        direction: str = "before"
    ) -> bool:
        """
        Cache paginated message results in Redis.
        
        Args:
            session_id: Chat session ID
            limit: Messages per page
            messages: List of message objects to cache
            next_cursor: Next pagination cursor
            total_count: Total messages in session
            has_more: Whether more messages exist
            cursor: Current pagination cursor
            direction: Pagination direction
            
        Returns:
            True if cache set successfully, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(session_id, limit, cursor, direction)
            
            # Serialize datetime objects to strings for JSON compatibility
            serialized_messages = self._serialize_messages(messages)
            
            cache_data = {
                "messages": serialized_messages,
                "next_cursor": next_cursor,
                "total_count": total_count,
                "has_more": has_more,
                "cached_at": datetime.utcnow().isoformat(),
                "session_id": session_id
            }

            # Set with TTL
            self.redis_client.setex(
                cache_key,
                CACHE_TTL_SECONDS,
                json.dumps(cache_data)
            )

            # Track session cache size (for monitoring)
            session_size_key = self._get_session_cache_key(session_id)
            current_size = self.redis_client.get(session_size_key)
            new_size = (int(current_size) if current_size else 0) + len(messages)
            
            if new_size <= MAX_MESSAGES_PER_SESSION:
                self.redis_client.setex(session_size_key, CACHE_TTL_SECONDS, new_size)
            
            logger.info(f"✅ Cache SET: {cache_key} ({len(messages)} messages, TTL: 24h)")
            return True

        except Exception as e:
            logger.error(f"❌ Error setting cache: {e}")
            return False

    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate all cached messages for a session.
        Use this when messages are updated or deleted.
        
        Args:
            session_id: Session to invalidate
            
        Returns:
            True if invalidation successful
        """
        if not self.redis_client:
            return False

        try:
            # Get all keys for this session and delete them
            pattern = f"{CACHE_KEY_PREFIX}:{session_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cache INVALIDATED: {len(keys)} keys for session {session_id}")
            
            return True

        except Exception as e:
            logger.warning(f"Error invalidating session cache: {e}")
            return False

    def invalidate_all(self) -> bool:
        """
        Clear all message caches. Use with caution in production.
        
        Returns:
            True if clearing successful
        """
        if not self.redis_client:
            return False

        try:
            pattern = f"{CACHE_KEY_PREFIX}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.warning(f"Cache CLEARED: Removed {len(keys)} total cache entries")
            
            return True

        except Exception as e:
            logger.warning(f"Error clearing all caches: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Get cache statistics for monitoring and debugging.
        
        Returns:
            Dictionary with cache stats (keys count, memory usage, etc.)
        """
        if not self.redis_client:
            return {"status": "disabled", "reason": "Redis not connected"}

        try:
            keys = self.redis_client.keys(f"{CACHE_KEY_PREFIX}:*")
            info = self.redis_client.info()
            
            return {
                "status": "active",
                "total_keys": len(keys),
                "used_memory": info.get("used_memory_human", "unknown"),
                "used_memory_bytes": info.get("used_memory", 0),
                "ttl_hours": CACHE_TTL_HOURS,
                "connected": True,
                "redis_version": info.get("redis_version", "unknown")
            }

        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {"status": "error", "reason": str(e)}

    def is_available(self) -> bool:
        """Check if Redis cache is available and connected."""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    def get_session_paper_id(self, session_id: str) -> Optional[str]:
        """
        Get cached session-to-paper mapping.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            Paper ID if cached, None if not found
        """
        if not self.redis_client:
            return None

        try:
            cache_key = f"auth:session:{session_id}:paper_id"
            paper_id = self.redis_client.get(cache_key)
            
            if paper_id:
                logger.info(f"✅ Auth Cache HIT: session {session_id[:8]}... -> paper {paper_id[:8]}...")
                return paper_id
            
            return None

        except Exception as e:
            logger.warning(f"❌ Error retrieving session auth cache: {e}")
            return None

    def set_session_paper_id(self, session_id: str, paper_id: str, ttl_seconds: int = 900) -> bool:
        """
        Cache session-to-paper mapping (15 min TTL default).
        
        Args:
            session_id: Chat session ID
            paper_id: Paper ID
            ttl_seconds: Cache expiration time (default 900s = 15min)
            
        Returns:
            True if cache set successfully
        """
        if not self.redis_client:
            return False

        try:
            cache_key = f"auth:session:{session_id}:paper_id"
            self.redis_client.setex(cache_key, ttl_seconds, paper_id)
            logger.info(f"✅ Auth Cache SET: session {session_id[:8]}... -> paper {paper_id[:8]}... (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Error setting session auth cache: {e}")
            return False

    def check_paper_ownership(self, paper_id: str, user_id: str) -> Optional[bool]:
        """
        Get cached paper ownership status.
        
        Args:
            paper_id: Paper ID
            user_id: User ID
            
        Returns:
            True if user owns paper, False if not, None if not cached
        """
        if not self.redis_client:
            return None

        try:
            cache_key = f"auth:paper:{paper_id}:user:{user_id}"
            ownership = self.redis_client.get(cache_key)
            
            if ownership is not None:
                result = ownership == "1"
                logger.info(f"✅ Auth Cache HIT: paper {paper_id[:8]}... owned by user {user_id[:8]}... = {result}")
                return result
            
            return None

        except Exception as e:
            logger.warning(f"❌ Error retrieving ownership auth cache: {e}")
            return None

    def set_paper_ownership(self, paper_id: str, user_id: str, owns: bool, ttl_seconds: int = 900) -> bool:
        """
        Cache paper ownership status (15 min TTL default).
        
        Args:
            paper_id: Paper ID
            user_id: User ID
            owns: Whether user owns the paper
            ttl_seconds: Cache expiration time (default 900s = 15min)
            
        Returns:
            True if cache set successfully
        """
        if not self.redis_client:
            return False

        try:
            cache_key = f"auth:paper:{paper_id}:user:{user_id}"
            self.redis_client.setex(cache_key, ttl_seconds, "1" if owns else "0")
            logger.info(f"✅ Auth Cache SET: paper {paper_id[:8]}... owned by user {user_id[:8]}... = {owns} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Error setting ownership auth cache: {e}")
            return False


# Singleton instance - use this throughout the application
message_cache_service = MessageCacheService()


# Convenience functions for easy access

def cache_get(
    session_id: str,
    limit: int,
    cursor: Optional[str] = None,
    direction: str = "before"
) -> Optional[Dict]:
    """Get cached messages."""
    return message_cache_service.get(session_id, limit, cursor, direction)


def cache_set(
    session_id: str,
    limit: int,
    messages: List[Dict],
    next_cursor: Optional[str],
    total_count: int,
    has_more: bool,
    cursor: Optional[str] = None,
    direction: str = "before"
) -> bool:
    """Set cached messages."""
    return message_cache_service.set(
        session_id, limit, messages, next_cursor, total_count, has_more, cursor, direction
    )


def cache_invalidate(session_id: str) -> bool:
    """Invalidate session cache."""
    return message_cache_service.invalidate_session(session_id)


def cache_stats() -> Dict:
    """Get cache statistics."""
    return message_cache_service.get_stats()


# Authorization cache convenience functions

def get_cached_session_paper(session_id: str) -> Optional[str]:
    """Get cached session-to-paper mapping."""
    return message_cache_service.get_session_paper_id(session_id)


def cache_session_paper(session_id: str, paper_id: str, ttl_seconds: int = 900) -> bool:
    """Cache session-to-paper mapping (15 min TTL default)."""
    return message_cache_service.set_session_paper_id(session_id, paper_id, ttl_seconds)


def get_cached_paper_ownership(paper_id: str, user_id: str) -> Optional[bool]:
    """Get cached paper ownership status."""
    return message_cache_service.check_paper_ownership(paper_id, user_id)


def cache_paper_ownership(paper_id: str, user_id: str, owns: bool, ttl_seconds: int = 900) -> bool:
    """Cache paper ownership status (15 min TTL default)."""
    return message_cache_service.set_paper_ownership(paper_id, user_id, owns, ttl_seconds)
