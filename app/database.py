"""
Database Connection and Session Management
Uses PostgreSQL with asyncpg
"""

from databases import Database
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Database URL
DATABASE_URL = settings.DATABASE_URL

# Create database instance for async queries
database = Database(DATABASE_URL)

# Create SQLAlchemy engine for migrations
engine = create_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://") 
    if "postgresql://" in DATABASE_URL else DATABASE_URL
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Metadata for models
metadata = MetaData()

# Base class for models
Base = declarative_base(metadata=metadata)


# Dependency to get database session
async def get_database():
    """Get database connection"""
    return database


# Context manager for database connection
async def connect_db():
    """Connect to database on startup"""
    await database.connect()
    print("[OK] Database connected")


async def disconnect_db():
    """Disconnect from database on shutdown"""
    await database.disconnect()
    print("[OK] Database disconnected")