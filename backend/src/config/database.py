from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config.settings import DATABASE_URL

connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


Session = sessionmaker(bind=engine, expire_on_commit=False)


def database():
    with Session() as db:
        yield db
