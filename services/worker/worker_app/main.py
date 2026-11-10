from worker_app.celery_app import create_celery_app

celery_app = create_celery_app()

__all__ = ["celery_app", "create_celery_app"]
