import logging
from src.utils.fault_tolerance import fault_tolerant

logger = logging.getLogger(__name__)

# This class is crucial for catching the error in main.py
class CircuitBreakerError(Exception):
    pass

@fault_tolerant()
def call_inventory_service(items: list) -> dict:
    """Simulates a call to an external inventory service."""
    logger.info("Attempting to call Inventory Service...")
    return {"status": "reserved"}

@fault_tolerant()
def call_payment_service(order_data: dict) -> dict:
    """Simulates a call to an external payment service."""
    logger.info("Attempting to call Payment Service...")
    return {"transaction_id": "tx123", "status": "approved"}
