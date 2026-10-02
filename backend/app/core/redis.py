import json
import logging
from typing import Optional, AsyncGenerator
import redis
import redis.asyncio as aioredis
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback in-memory event queue for testing / offline redis
_fallback_subscribers = []

def get_redis_client() -> Optional[redis.Redis]:
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        return r
    except Exception as e:
        logger.warning(f"Redis not available ({e}). Using in-memory pub/sub fallback.")
        return None

def publish_alert_sync(alert_payload: dict):
    client = get_redis_client()
    msg_str = json.dumps(alert_payload)
    if client:
        try:
            client.publish("alerts", msg_str)
            return
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
    
    # Broadcast to in-memory fallback subscribers
    for queue in _fallback_subscribers:
        try:
            queue.put_nowait(msg_str)
        except Exception:
            pass

def register_fallback_subscriber(queue):
    _fallback_subscribers.append(queue)

def unregister_fallback_subscriber(queue):
    if queue in _fallback_subscribers:
        _fallback_subscribers.remove(queue)
