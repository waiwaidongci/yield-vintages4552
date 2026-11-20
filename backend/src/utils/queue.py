"""查账任务队列：容器内使用 Redis（rpush/lpop），本地无 Redis 时退化为内存队列。"""
import json
import threading
from collections import deque

from src.config.settings import REDIS_URL, QUEUE_FALLBACK

_MEMORY_QUEUE = deque()
_MEM_LOCK = threading.Lock()
_redis = None
_redis_tried = False


def _client():
    global _redis, _redis_tried
    if not _redis_tried:
        _redis_tried = True
        try:
            import redis
            c = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2)
            c.ping()
            _redis = c
        except Exception:
            _redis = None
    return _redis


def push(name, value):
    c = _client()
    if c is not None:
        c.rpush(name, json.dumps(value))
    elif QUEUE_FALLBACK == 'memory':
        with _MEM_LOCK:
            _MEMORY_QUEUE.append((name, value))
    else:
        raise RuntimeError('Redis 不可用且未允许内存队列退化')


def pop(name):
    c = _client()
    if c is not None:
        item = c.lpop(name)
        return json.loads(item) if item else None
    with _MEM_LOCK:
        while _MEMORY_QUEUE:
            q, value = _MEMORY_QUEUE.popleft()
            if q == name:
                return value
    return None
