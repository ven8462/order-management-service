from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from . import services
from .models import Cart, Order, OrderItem, OrderTracking
from .serializers import (
    CartItemCreateSerializer,
    CartSerializer,
    OrderCreateSerializer,
    OrderReadSerializer,
    OrderStatusUpdateSerializer,
    ProductSearchResultSerializer,
)

from kafka_utils.producer import publish_event


# Product search proxy
@api_view(["GET"])
def product_search(request: Request) -> Response:
    q = request.GET.get("query", "")
    category = request.GET.get("category")
    limit = int(request.GET.get("limit", 10))
    page = int(request.GET.get("page", 1))

    res = services.product_search(q, category=category, limit=limit, page=page)

    serializer = ProductSearchResultSerializer(res["products"], many=True)
    return Response({"products": serializer.data, "pagination": res["pagination"]})


class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]  # adjust as needed
    queryset = Cart.objects.all()

    @action(detail=False, methods=["post"])
    def items(self, request: Request) -> Response:
        """POST /api/cart/items/."""
        data = request.data.copy()
        cart_id = data.get("cart")

        if not cart_id:
            cart = Cart.objects.create(user_id=data["user_id"])
            data["cart"] = cart.id

        serializer = CartItemCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        return Response(
            {
                "cartId": item.cart.id,
                "items": CartSerializer(item.cart).data["items"],
                "totalAmount": str(item.cart.total_amount()),
            },
            status=status.HTTP_201_CREATED,
        )


class OrderViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    queryset = Order.objects.all()

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderReadSerializer(order)
        return Response(serializer.data)

    def create(self, request: Request) -> Response:
        """POST /api/orders/ """
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = str(data["user_id"])
        items = data["items"]
        address_id = data["address_id"]
        payment_method_id = data["payment_method_id"]
        currency = data.get("currency", "USD")
        idempotency_key = data.get("idempotency_key")

        # Calculate total amount
        total = sum(Decimal(str(it["price"])) * int(it["quantity"]) for it in items)

        # Create the order
        order = Order.objects.create(
            user_id=user_id,
            status=Order.Status.PENDING,
            total_amount=total,
            currency=currency,
            address_id=address_id,
            payment_method_id=payment_method_id,
        )

        # Create order items
        order_items = [
            OrderItem(
                order=order,
                product_id=it["product_id"],
                quantity=it["quantity"],
                price=it["price"],
                subtotal=Decimal(str(it["price"])) * int(it["quantity"]),
            )
            for it in items
        ]
        OrderItem.objects.bulk_create(order_items)

        # Initial tracking event
        OrderTracking.objects.create(
            order=order,
            status=Order.Status.PENDING,
            location="Order Created",
        )

        # Emit OrderCreated event for downstream services
        publish_event(
            "order-created",
            {
                "order_id": str(order.id),
                "user_id": user_id,
                "items": [
                    {
                        "product_id": str(it["product_id"]),
                        "quantity": it["quantity"],
                        "price": str(it["price"]),
                    }
                    for it in items
                ],
                "total_amount": str(total),
                "currency": currency,
                "address_id": address_id,
                "payment_method_id": payment_method_id,
                "idempotency_key": idempotency_key,
            },
        )

        return Response(OrderReadSerializer(order).data, status=status.HTTP_201_CREATED)



    @action(detail=True, methods=["put"])
    def status(self, request: Request, pk: str | None = None) -> Response:
        """PUT /api/orders/{order_id}/status/."""
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["new_status"]

        # Allowed transitions
        allowed = {
            Order.Status.PENDING: {
                Order.Status.CONFIRMED,
                Order.Status.CANCELLED,
                Order.Status.PAID,

            },
            Order.Status.CONFIRMED: {
                Order.Status.SHIPPED,
                Order.Status.CANCELLED,
            },
            Order.Status.SHIPPED: {Order.Status.DELIVERED},
            Order.Status.DELIVERED: set(),
            Order.Status.CANCELLED: set(),
        }
        if new_status not in allowed.get(order.status, set()):
            return Response(
                {"detail": f"Illegal transition {order.status} → {new_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderTracking.objects.create(
            order=order,
            status=new_status,
            location=request.data.get("location", None),
        )
        return Response(OrderReadSerializer(order).data)

    @action(detail=True, methods=["get"])
    def tracking(self, request: Request, pk: str | None = None) -> Response:
        order = get_object_or_404(Order, pk=pk)
        events = order.tracking_events.order_by("timestamp").all()
        data = [
            {
                "status": e.status,
                "timestamp": e.timestamp,
                "location": e.location,
            }
            for e in events
        ]
        return Response(
            {
                "orderId": str(order.id),
                "currentStatus": order.status,
                "trackingEvents": data,
            },
        )
