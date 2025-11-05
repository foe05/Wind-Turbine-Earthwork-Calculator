"""
Celery worker configuration for background jobs
"""
from celery import Celery
import os
import logging

logger = logging.getLogger(__name__)

# Celery instance
celery_app = Celery(
    "geo_engineering_worker",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0")
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Berlin',
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # Results expire after 1 hour
)

# Auto-discover tasks from tasks module
celery_app.autodiscover_tasks(['app.tasks'])


@celery_app.task(name='app.worker.health_check')
def health_check():
    """Celery health check task"""
    return {"status": "healthy", "message": "Celery worker is running"}
