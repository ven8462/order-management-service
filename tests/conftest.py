import pytest
from orders.models import Order

@pytest.fixture
def pending_order(db):
    """Create a simple pending order."""
    return Order.objects.create(status=Order.Status.PENDING)