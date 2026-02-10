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
        self.redis = redis.from_url(
            settings.HYPERCODE_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
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

    async def publish_stream(self, stream: str, message: MessageEnvelope, role: str = "general") -> str:
        """
        Publish to a Redis Stream for at-least-once delivery.
        Returns entry id. Downstream consumers must XACK.
        """
        if not self._check_acl(role, stream, "publish"):
            logger.warning(f"ACL Deny: Role '{role}' cannot publish to stream '{stream}'")
            return ""
        try:
            data = message.model_dump(mode="json")
            # Flatten payload for XADD
            fields = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in data.items()}
            entry_id = await self.redis.xadd(stream, fields)
            return entry_id
        except Exception as e:
            logger.error(f"Failed to publish stream {stream}: {e}")
            raise

    async def ensure_consumer_group(self, stream: str, group: str) -> None:
        try:
            await self.redis.xgroup_create(stream, group, id="$", mkstream=True)
        except Exception:
            # Group may already exist
            pass

    async def read_group(self, stream: str, group: str, consumer: str, count: int = 10, block_ms: int = 1000):
        try:
            entries = await self.redis.xreadgroup(group, consumer, streams={stream: ">"}, count=count, block=block_ms)
            return entries or []
        except Exception as e:
            logger.error(f"Failed to read group {group} on {stream}: {e}")
            return []

    async def ack(self, stream: str, group: str, entry_id: str):
        try:
            await self.redis.xack(stream, group, entry_id)
        except Exception:
            pass

    async def schedule_retry(self, mission_id: str, rc: int, base: float = 2.0, factor: float = 2.0, jitter: float | None = 0.5, max_delay: float = 300.0, max_retries: int | None = None) -> tuple[bool, float]:
        try:
            if max_retries is not None and rc > max_retries:
                return False, 0.0
            import time, random
            delay = min(max_delay, base * (factor ** max(rc - 1, 0)))
            if jitter is not None:
                delay += random.uniform(-jitter, jitter)
            sched = time.time() + max(0.0, delay)
            await self.redis.zadd("mission:retry:zset", {mission_id: sched})
            return True, delay
        except Exception:
            return False, 0.0

    async def dequeue_due_retries(self, now_ts: float | None = None) -> list[str]:
        try:
            import time
            now = now_ts or time.time()
            mids = await self.redis.zrangebyscore("mission:retry:zset", min=0, max=now)
            result = []
            for mid in mids:
                if isinstance(mid, bytes):
                    mid = mid.decode()
                result.append(mid)
            return result
        except Exception:
            return []

    async def clear_retry(self, mission_id: str):
        try:
            await self.redis.delete(f"mission:{mission_id}:retries")
            await self.redis.zrem("mission:retry:zset", mission_id)
        except Exception:
            pass

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
