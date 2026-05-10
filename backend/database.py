import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.models import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Drop and recreate all tables to ensure schema is up-to-date."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
