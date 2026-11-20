import os, json
from pathlib import Path

# 容器内 project.json 位于 /app；本地开发允许从仓库根读取
_candidates = [Path('/app/project.json'), Path(__file__).resolve().parents[2] / 'project.json']
CONFIG = json.loads(next(p for p in _candidates if p.exists()).read_text(encoding='utf-8'))

# 默认 SQLite 便于无 MySQL 的本地测试；容器通过 DATABASE_URL 使用 MySQL8
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///' + str(Path(__file__).resolve().parents[2] / 'local_dev.sqlite3'))
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
SECRET = os.getenv('JWT_SECRET', 'local-dev-secret-change-before-production')
# 无 Redis 时（本地开发）退化为内存队列，行为与 rpush/lpop 一致
QUEUE_FALLBACK = os.getenv('QUEUE_FALLBACK', 'memory')
