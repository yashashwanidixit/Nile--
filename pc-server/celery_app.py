from celery import Celery


celery_app = Celery(
    "hotel_agent",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["task"] 
)