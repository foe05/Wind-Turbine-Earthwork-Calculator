"""
Initialize database tables
"""
import logging
from sqlalchemy.exc import OperationalError
from app.db.database import engine, Base
from app.models import user  # Import models to register them

logger = logging.getLogger(__name__)


def init_db():
    """
    Create all database tables if they don't exist
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except OperationalError as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
