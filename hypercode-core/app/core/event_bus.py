import os
import json
import redis.asyncio as redis

REDIS_URL = os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0")

class EventBus:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)

    async def publish(self, channel: str, message: dict):
        """Publish a message to a specific channel."""
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str):
        """Subscribe to a channel and yield messages."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])

event_bus = EventBus()
