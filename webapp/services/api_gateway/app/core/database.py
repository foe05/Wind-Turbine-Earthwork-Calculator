"""
Database connection utilities
"""
import psycopg2
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret@postgres:5432/geo_engineering")


def get_db_connection():
    """
    Get database connection

    Returns:
        psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
