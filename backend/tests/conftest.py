import os
import tempfile

_tmp = tempfile.mkdtemp(prefix='cif-test-')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{_tmp}/test.sqlite3')
os.environ.setdefault('JWT_SECRET', 'test-secret')
os.environ.setdefault('QUEUE_FALLBACK', 'memory')
os.environ.setdefault('SEED_DEMO', 'false')

import pytest  # noqa: E402
from src.config.database import Base, engine, Session  # noqa: E402
from src.models.entities import User  # noqa: E402
from src.utils.security import password_hash  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session() as session:
        for role in ('admin', 'analyst', 'viewer'):
            session.add(User(email=f'{role}@demo.local', role=role,
                             password=password_hash('Demo2026!')))
        session.commit()
        yield session


class _U:
    def __init__(self, email):
        self.email = 'admin@demo.local'
