import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.database import Base, engine
from src.config.settings import CONFIG
from src.models import entities  # noqa: F401
from src.routes import auth, records, audits, logs
from src.middlewares.errors import Errors
from src.middlewares.rate import RateLimit


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO') == 'true':
        try:
            from scripts.seed_demo import seed
            seed()
        except Exception:
            logging.exception('seed失败，可手动重试')
    yield


app = FastAPI(title=CONFIG['title'], lifespan=lifespan)
app.add_middleware(Errors)
app.add_middleware(RateLimit)
for module in (auth, records, audits, logs):
    app.include_router(module.router)


@app.get('/health')
def health():
    from sqlalchemy import text
    with engine.connect() as c:
        c.execute(text('SELECT 1'))
    queue = 'redis'
    try:
        from src.utils.queue import _client
        if _client() is None:
            queue = 'memory-fallback'
    except Exception:
        queue = 'memory-fallback'
    return {'status': 'healthy', 'queue': queue}


@app.get('/meta')
def meta():
    return CONFIG
