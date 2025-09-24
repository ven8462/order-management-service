import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_amount(self) -> Decimal:
        return sum((item.price * item.quantity) for item in self.items.all()) or Decimal("0.00")


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product_id = models.UUIDField()
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)  # snapshot price at add-to-cart
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"
        SHIPPED = "SHIPPED"
        DELIVERED = "DELIVERED"
        CANCELLED = "CANCELLED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    currency = models.CharField(max_length=8, default="USD")
    address_id = models.CharField(max_length=128, blank=True, null=True)
    payment_method_id = models.CharField(max_length=128, blank=True, null=True)
    payment_transaction_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product_id = models.UUIDField()
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)  # final snapshot price
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderTracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name="tracking_events", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Order.Status.choices)
    timestamp = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=255, blank=True, null=True)
