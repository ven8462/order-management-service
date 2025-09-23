import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("order_management_service")

# Use Redis as broker
app.conf.broker_url = "redis://redis:6379/0"

# Optional: store results in Redis too
app.conf.result_backend = "redis://redis:6379/0"

# Auto-discover tasks from your apps
app.autodiscover_tasks()