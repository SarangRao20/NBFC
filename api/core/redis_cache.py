"""Redis Cache Manager for NBFC Loan System

Provides caching for sessions, customer data, and performance optimization.
"""

import json
import pickle
from typing import Any, Optional, Dict, List
from datetime import timedelta
import redis.asyncio as redis
from api.config import get_settings

settings = get_settings()

class RedisCache:
    """Redis cache wrapper for NBFC system"""
    
    def __init__(self):
        self.redis_client = None
        self.connected = False
        
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            print("✅ Redis connected successfully")
            return True
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
            print("🔌 Redis disconnected")
    
    async def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.connected
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set a value in cache"""
        if not self.connected:
            return False
        
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            elif not isinstance(value, str):
                value = str(value)
            
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            print(f"❌ Redis SET error for key '{key}': {e}")
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache"""
        if not self.connected:
            return default
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return default
            
            # Try to parse as JSON first
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"❌ Redis GET error for key '{key}': {e}")
            return default
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self.connected:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"❌ Redis DELETE error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.connected:
            return False
        
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            print(f"❌ Redis EXISTS error for key '{key}': {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session from cache"""
        return await self.get(f"session:{session_id}")
    
    async def set_session(self, session_id: str, session_data: Dict) -> bool:
        """Set session in cache"""
        return await self.set(f"session:{session_id}", session_data)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from cache"""
        return await self.delete(f"session:{session_id}")
    
    async def get_customer(self, phone: str) -> Optional[Dict]:
        """Get customer data from cache"""
        return await self.get(f"customer:{phone}")
    
    async def set_customer(self, phone: str, customer_data: Dict) -> bool:
        """Set customer data in cache"""
        return await self.set(f"customer:{phone}", customer_data, ttl=7200)  # 2 hours
    
    async def get_loan_history(self, phone: str) -> Optional[List]:
        """Get loan history from cache"""
        return await self.get(f"loan_history:{phone}")
    
    async def set_loan_history(self, phone: str, history: List) -> bool:
        """Set loan history in cache"""
        return await self.set(f"loan_history:{phone}", history, ttl=1800)  # 30 minutes
    
    async def get_otp(self, phone: str) -> Optional[str]:
        """Get OTP from cache"""
        return await self.get(f"otp:{phone}")
    
    async def set_otp(self, phone: str, otp: str) -> bool:
        """Set OTP in cache"""
        return await self.set(f"otp:{phone}", otp, ttl=300)  # 5 minutes
    
    async def delete_otp(self, phone: str) -> bool:
        """Delete OTP from cache"""
        return await self.delete(f"otp:{phone}")
    
    async def get_conversation_memory(self, session_id: str) -> Optional[List]:
        """Get conversation memory from cache"""
        return await self.get(f"conversation:{session_id}")
    
    async def set_conversation_memory(self, session_id: str, messages: List) -> bool:
        """Set conversation memory in cache"""
        return await self.set(f"conversation:{session_id}", messages, ttl=5400)  # 90 minutes
    
    async def add_conversation_message(self, session_id: str, message: Dict) -> bool:
        """Add a message to conversation memory"""
        memory = await self.get_conversation_memory(session_id) or []
        memory.append(message)
        # Keep only last 20 messages
        if len(memory) > 20:
            memory = memory[-20:]
        return await self.set_conversation_memory(session_id, memory)
    
    async def clear_user_cache(self, phone: str) -> bool:
        """Clear all cache entries for a user"""
        keys_to_delete = [
            f"customer:{phone}",
            f"loan_history:{phone}",
            f"otp:{phone}"
        ]
        success = True
        for key in keys_to_delete:
            if not await self.delete(key):
                success = False
        return success
    
    async def get_cache_stats(self) -> Dict:
        """Get Redis cache statistics"""
        if not self.connected:
            return {"error": "Redis not connected"}
        
        try:
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "Unknown"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            return {"error": str(e)}

# Global cache instance
cache = RedisCache()


async def get_cache() -> RedisCache:
    """Get the global cache instance"""
    if not cache.connected:
        await cache.connect()
    return cache


# Cache decorator for functions
def cache_result(key_template: str, ttl: int = None):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_instance = await get_cache()
            
            # Generate cache key
            cache_key = key_template.format(*args, **kwargs)
            
            # Try to get from cache first
            cached_result = await cache_instance.get(cache_key)
            if cached_result is not None:
                print(f"🎯 Cache HIT for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            print(f"⚡ Cache MISS for {cache_key}")
            result = await func(*args, **kwargs)
            await cache_instance.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
