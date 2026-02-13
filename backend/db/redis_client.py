import redis.asyncio as redis
import os
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any


class _JSONEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and datetime types from the database."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

    async def connect(self):
        """Create Redis connection"""
        try:
            self.client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', None),
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self.pubsub:
            await self.pubsub.close()
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def set(self, key: str, value: Any, expiry: int = 300):
        """Set key-value pair with optional expiry in seconds"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, cls=_JSONEncoder)
        await self.client.set(key, value, ex=expiry)

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def delete(self, key: str):
        """Delete key"""
        await self.client.delete(key)

    async def publish(self, channel: str, message: Any):
        """Publish message to channel"""
        if isinstance(message, (dict, list)):
            message = json.dumps(message, cls=_JSONEncoder)
        await self.client.publish(channel, message)

    async def subscribe(self, channel: str):
        """Subscribe to channel"""
        if not self.pubsub:
            self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(channel)
        return self.pubsub

# Global Redis instance
redis_client = RedisClient()
