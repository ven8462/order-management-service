import logging

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from . import api, consumer, models
from .database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Order Management Service",
    description="Manages orders, carts, and provides monitoring endpoints.",
)


@app.on_event("startup")
def on_startup() -> None:
    models.Base.metadata.create_all(bind=engine)

    consumer.start_consumer_thread()


app.include_router(api.order_router)
app.include_router(api.cart_router)
app.include_router(api.monitoring_router)


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
