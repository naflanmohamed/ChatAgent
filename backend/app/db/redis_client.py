import json
import redis
from app.core.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

CACHE_TTL_SECONDS = 60 * 30  # 30 minutes


def _key(conversation_id: str) -> str:
    return f"conversation:{conversation_id}:messages"


def get_cached_messages(conversation_id: str) -> list | None:
    """Returns cached messages as a list of dicts, or None if not cached (cache miss)."""
    raw = redis_client.get(_key(conversation_id))
    if raw is None:
        return None
    return json.loads(raw)


def set_cached_messages(conversation_id: str, messages: list[dict]) -> None:
    redis_client.set(_key(conversation_id), json.dumps(messages), ex=CACHE_TTL_SECONDS)


def invalidate_cache(conversation_id: str) -> None:
    redis_client.delete(_key(conversation_id))


    #          Request
    #             │
    #             ▼
    #          Redis
    #             │
    #       ┌─────┴─────┐
    #       │           │
    #    Found        Not Found
    #    Hit            Miss
    #       │             │
    #       ▼             ▼
    #    Return      PostgreSQL
    #    messages        │
    #                    ▼
    #               Get messages
    #                    │
    #                    ▼
    #               Save to Redis
    #                    │
    #                    ▼
    #               Return messages