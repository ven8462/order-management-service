# File: order_service/main.py
"""
This is the main entry point for the FastAPI application.
It initializes the app, creates database tables, includes API routers,
starts the background consumer, and exposes a /metrics endpoint.
"""

import logging
from fastapi import FastAPI
# --- NEW: Import the prometheus client ---
from prometheus_client import make_asgi_app

from . import api, consumer, models
from .database import engine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# This line ensures that all tables defined in models.py are created in the database
# when the application starts. For production, you would use Alembic migrations.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order Management Service",
    description="Manages the lifecycle of customer orders using a Saga pattern.",
    version="1.0.0"
)

# --- NEW: Create a separate ASGI app for the /metrics endpoint ---
# This creates a small, standalone app that knows how to render the Prometheus metrics.
metrics_app = make_asgi_app()

@app.on_event("startup")
def on_startup():
    logger.info("Application starting up...")
    logger.info("Starting Kafka consumer thread...")
    # Start the Kafka consumer in a background thread
    consumer.start_consumer_thread()
    logger.info("Kafka consumer thread started.")

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Application shutting down...")

# Include the main API router for the /orders endpoints
app.include_router(api.router)

# --- NEW: Mount the metrics app at the /metrics path ---
# This tells FastAPI: "Any request to /metrics should be handled by the metrics_app".
app.mount("/metrics", metrics_app)

logger.info("Application setup complete.")