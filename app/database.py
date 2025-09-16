import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import make_url

# Load .env (VS Code terminals sometimes don't inject env vars)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# No sqlite-only flags; pick connect_args only when needed
url = make_url(DATABASE_URL)
connect_args = {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,   # empty for Postgres
    pool_pre_ping=True,          # helps recycle stale connections
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
