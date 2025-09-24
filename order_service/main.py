import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from . import api, consumer, models
from .database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application starting up... Creating database tables.")
    models.Base.metadata.create_all(bind=engine)
    consumer.start_consumer_thread()
    logging.info("Startup complete.")
    yield
    logging.info("Application shutting down...")


app = FastAPI(
    title="Order Management Service",
    description="Manages orders, carts, and provides monitoring endpoints.",
    lifespan=lifespan,
)

app.include_router(api.order_router)
app.include_router(api.cart_router)
app.include_router(api.monitoring_router)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
