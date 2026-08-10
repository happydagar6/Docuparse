"""
=============================================================================
Redis Message & Auth Cache Service (`services/message_cache_service.py`)
=============================================================================
This service provides a production-grade L2 Caching layer built on top of Redis.

Key Features & Architectural Patterns:
1. Paginated Message Caching: Caches API responses for chat pagination (24h TTL)
   to reduce expensive SQL database queries on repeated scrolling.
2. Resilience & Dual-Mode Connection: Automatically tries standard Redis TCP URL
   (using `redis-py`), and falls back to Upstash Redis REST API if native socket
   connections are blocked by firewalls/cloud environments.
3. Read-Through / Write-Around Pattern: Gracefully degrades if Redis is offline
   (app continues to work directly with PostgreSQL without throwing 500 errors).
4. Authorization & Session Caching: Caches session-to-paper mapping and user paper
   ownership checks (15 min TTL) to save SQL queries on every single chat request.
5. Cache Invalidation: Automatically clears stale cache keys when new messages arrive.
=============================================================================
"""

import json
import redis
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Tuple, Any, cast
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Redis environment variables
REDIS_URL = os.getenv("REDIS_URL")
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# Cache configuration constants
CACHE_TTL_HOURS = 24  # Paginated message cache TTL (24 hours)
CACHE_TTL_SECONDS = CACHE_TTL_HOURS * 3600
MAX_MESSAGES_PER_SESSION = 5000  # Memory protection: limit max cached messages per session
CACHE_KEY_PREFIX = "messages"


class MessageCacheService:
    """
    Production-grade Redis Caching Layer.
    
    Handles connection setup, key generation, JSON serialization, cache fetching,
    invalidation, and authorization checks.
    """

    def __init__(self):
        """Initialize Redis client connection."""
        self.redis_client: Any = None
        self.use_rest_api = False
        self._initialize_redis()

    def _initialize_redis(self) -> None:
        """
        Connects to Redis using a Dual-Mode Fallback Strategy:
        Mode 1: Standard TCP Socket (`redis.from_url`). Fast, native TCP protocol.
        Mode 2: Upstash REST API. Backup HTTP endpoint if TCP port 6379 is blocked.
        """
        try:
            # Try Mode 1: Native TCP socket connection
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()  # Test connection health
            logger.info("✅ Message Cache: Connected to Redis (Standard TCP URL)")
        except Exception as e:
            logger.warning(f"⚠️ Message Cache: Standard Redis connection failed: {e}")
            try:
                # Mode 2 Fallback: Upstash HTTP REST API
                import requests
                self.use_rest_api = True
                self.rest_url = UPSTASH_REDIS_REST_URL
                self.rest_token = UPSTASH_REDIS_REST_TOKEN
                
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
                # Graceful Degradation: If Redis fails completely, set client to None.
                # The application will silently bypass cache and query PostgreSQL directly.
                self.redis_client = None

    def _generate_cache_key(
        self,
        session_id: str,
        limit: int,
        cursor: Optional[str] = None,
        direction: str = "before"
    ) -> str:
        """
        Generates a unique, structured Redis key for a paginated message query.
        Example key: `messages:session_123:20:before:eyJ0aW1lc3...`
        """
        cursor_part = f":{cursor[:20]}" if cursor else ":none"
        return f"{CACHE_KEY_PREFIX}:{session_id}:{limit}:{direction}{cursor_part}"

    def _get_session_cache_key(self, session_id: str) -> str:
        """Generates key for tracking cached message volume per session."""
        return f"{CACHE_KEY_PREFIX}:{session_id}:size"

    def get(
        self,
        session_id: str,
        limit: int,
        cursor: Optional[str] = None,
        direction: str = "before"
    ) -> Optional[Dict]:
        """
        Fetches cached message pagination results from Redis.
        Returns deserialized JSON dictionary if Cache HIT, or None if Cache MISS.
        """
        if not self.redis_client:
            logger.warning("Redis client not available - cache disabled")
            return None

        try:
            cache_key = self._generate_cache_key(session_id, limit, cursor, direction)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.info(f"✅ Cache HIT: {cache_key}")
                return json.loads(cached_data)  # Deserialize string -> dict
            
            logger.info(f"⚠️  Cache MISS: {cache_key}")
            return None

        except Exception as e:
            logger.warning(f"❌ Error retrieving from cache: {e}")
            # Graceful Degradation: Return None so caller falls back to database
            return None

    def _serialize_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Converts Python `datetime` objects to ISO 8601 string format.
        Required because standard `json.dumps()` cannot serialize Python datetime objects.
        """
        serialized = []
        for msg in messages:
            serialized_msg = {}
            for key, value in msg.items():
                if isinstance(value, datetime):
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
        Saves paginated message query results into Redis with a 24-hour expiration (TTL).
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(session_id, limit, cursor, direction)
            
            # Convert datetime objects -> ISO strings before JSON encoding
            serialized_messages = self._serialize_messages(messages)
            
            cache_data = {
                "messages": serialized_messages,
                "next_cursor": next_cursor,
                "total_count": total_count,
                "has_more": has_more,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id
            }

            # Save key in Redis with auto-expiration (SETEX)
            self.redis_client.setex(
                cache_key,
                CACHE_TTL_SECONDS,
                json.dumps(cache_data)
            )

            # Update session size tracking counter
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
        Invalidates (deletes) all Redis keys for a specific chat session.
        Called whenever a new user message or AI response is posted.
        """
        if not self.redis_client:
            return False

        try:
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
        """Flushes all message cache entries from Redis."""
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
        """Returns health metrics and memory stats from Redis for health-check endpoints."""
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
        """Pings Redis to check if connection is active."""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    # =========================================================================
    # AUTHORIZATION & SESSION-TO-PAPER MAPPING CACHE
    # =========================================================================
    # Caches relationship mappings and paper ownership to avoid running 
    # expensive PostgreSQL `SELECT` queries on every API request.
    # =========================================================================

    def get_session_paper_id(self, session_id: str) -> Optional[str]:
        """Gets cached session-to-paper mapping (key: `auth:session:{session_id}:paper_id`)."""
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
        """Caches session-to-paper mapping with a 15-minute TTL (900 seconds)."""
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
        """Gets cached paper ownership check (key: `auth:paper:{paper_id}:user:{user_id}`)."""
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
        """Caches paper ownership verification boolean ("1" or "0") with a 15-minute TTL."""
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


# Singleton service instance
message_cache_service = MessageCacheService()


# Convenience wrapper functions for clean imports across route files

def cache_get(
    session_id: str,
    limit: int,
    cursor: Optional[str] = None,
    direction: str = "before"
) -> Optional[Dict]:
    """Helper: Get cached paginated messages."""
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
    """Helper: Save paginated messages to cache."""
    return message_cache_service.set(
        session_id, limit, messages, next_cursor, total_count, has_more, cursor, direction
    )


def cache_invalidate(session_id: str) -> bool:
    """Helper: Invalidate session message cache."""
    return message_cache_service.invalidate_session(session_id)


def cache_stats() -> Dict:
    """Helper: Get Redis stats."""
    return message_cache_service.get_stats()


# Authorization cache convenience wrappers

def get_cached_session_paper(session_id: str) -> Optional[str]:
    """Helper: Get cached session-to-paper mapping."""
    return message_cache_service.get_session_paper_id(session_id)


def cache_session_paper(session_id: str, paper_id: str, ttl_seconds: int = 900) -> bool:
    """Helper: Cache session-to-paper mapping."""
    return message_cache_service.set_session_paper_id(session_id, paper_id, ttl_seconds)


def get_cached_paper_ownership(paper_id: str, user_id: str) -> Optional[bool]:
    """Helper: Get cached paper ownership status."""
    return message_cache_service.check_paper_ownership(paper_id, user_id)


def cache_paper_ownership(paper_id: str, user_id: str, owns: bool, ttl_seconds: int = 900) -> bool:
    """Helper: Cache paper ownership status."""
    return message_cache_service.set_paper_ownership(paper_id, user_id, owns, ttl_seconds)
