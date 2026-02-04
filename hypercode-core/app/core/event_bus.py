import os
import json
import redis.asyncio as redis
from prometheus_client import Histogram

REDIS_URL = os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0")

class EventBus:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)
        self._latency = Histogram(
            "event_bus_latency_seconds",
            "Latency of EventBus operations",
            ("operation",),
            buckets=(0.0005, 0.001, 0.005, 0.01, 0.05)
        )

    async def publish(self, channel: str, message: dict):
        """Publish a message to a specific channel."""
        import time
        t0 = time.perf_counter()
        await self.redis.publish(channel, json.dumps(message))
        self._latency.labels("publish").observe(time.perf_counter() - t0)

    async def subscribe(self, channel: str):
        """Subscribe to a channel and yield messages."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                payload = json.loads(message["data"])
                yield payload

event_bus = EventBus()
