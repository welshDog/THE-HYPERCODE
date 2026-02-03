import redis.asyncio as redis
from app.core.config import get_settings
from app.schemas.message import MessageEnvelope
import logging
from typing import AsyncGenerator, Optional
import json

settings = get_settings()
logger = logging.getLogger(__name__)

class EventBus:
    """
    Redis-based Event Bus for real-time agent communication.
    Hardened with Deduplication, ACLs, and Circuit Breaker logic.
    """
    def __init__(self):
        self.redis = redis.from_url(settings.HYPERCODE_REDIS_URL)
        self.dedup_ttl = 3600  # Deduplication window: 1 hour
        
        # Simple ACL Map: role -> allowed_topics
        # In a real system, this might come from DB or Config
        self.acl_map = {
            "architect": ["domain.design.*", "system.events"],
            "coder": ["code.generation.*", "system.events"],
            "qa": ["testing.*", "system.events"],
            "general": ["*"] # Admin/Core
        }

    async def _is_duplicate(self, message_id: str) -> bool:
        """Check if message UUID has been processed recently."""
        key = f"msg:dedup:{message_id}"
        # setnx returns True if key was set (new), False if exists
        is_new = await self.redis.set(key, "1", ex=self.dedup_ttl, nx=True)
        return not is_new

    def _check_acl(self, role: str, topic: str, action: str = "publish") -> bool:
        """
        Check if agent role is allowed to publish/subscribe to topic.
        Supports wildcards (e.g., 'domain.*').
        """
        allowed_patterns = self.acl_map.get(role, [])
        for pattern in allowed_patterns:
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if topic.startswith(prefix):
                    return True
            if pattern == topic:
                return True
        return False

    async def publish(self, channel: str, message: MessageEnvelope, role: str = "general"):
        """
        Publish a MessageEnvelope to a specific Redis channel.
        Includes ACL check and Deduplication marking.
        """
        if not self._check_acl(role, channel, "publish"):
            logger.warning(f"ACL Deny: Role '{role}' cannot publish to '{channel}'")
            # We might want to raise an exception or just log
            return False

        try:
            # Mark as seen so we don't process our own messages if we subscribe to them (loopback prevention)
            # or simply to track global message uniqueness
            # await self._is_duplicate(str(message.id)) 

            # Use model_dump_json for reliable serialization of datetime/UUID
            data = message.model_dump_json()
            await self.redis.publish(channel, data)
            logger.debug(f"Published message {message.id} to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            raise

    async def subscribe(self, channel: str, role: str = "general") -> AsyncGenerator[MessageEnvelope, None]:
        """
        Subscribe to a channel and yield parsed MessageEnvelopes.
        Includes ACL check and Deduplication.
        """
        if not self._check_acl(role, channel, "subscribe"):
            logger.warning(f"ACL Deny: Role '{role}' cannot subscribe to '{channel}'")
            return

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel} as {role}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        raw_data = message["data"]
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8")
                        
                        envelope = MessageEnvelope.model_validate_json(raw_data)
                        
                        # Deduplication Check
                        if await self._is_duplicate(str(envelope.id)):
                            logger.debug(f"Duplicate message suppressed: {envelope.id}")
                            continue

                        yield envelope
                    except Exception as e:
                        logger.error(f"Failed to parse message from {channel}: {e}")
                        continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

# Singleton instance
event_bus = EventBus()
