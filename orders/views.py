import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from . import services
from .models import Cart, Order, OrderTracking
from .serializers import (
    CartItemCreateSerializer,
    CartSerializer,
    OrderCreateSerializer,
    OrderReadSerializer,
    OrderStatusUpdateSerializer,
    ProductSearchResultSerializer,
)
from .services import order_processing
from .services.external_apis import (
    InventoryReservationError,
    PaymentAuthorizationError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


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
    permission_classes = [AllowAny]
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
        """POST /api/orders/."""
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order = order_processing.create_order_saga(
                user_id=str(data["user_id"]),
                items=data["items"],
                address_id=data["address_id"],
                payment_method_id=data["payment_method_id"],
                currency=data.get("currency", "USD"),
                idempotency_key=data.get("idempotency_key"),
            )
            read_serializer = OrderReadSerializer(order)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)

        except InventoryReservationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        except PaymentAuthorizationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        except ServiceUnavailableError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception:
            logger.exception("An unexpected error occurred during order creation.")
            return Response(
                {"detail": "An internal server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["put"])
    def status(self, request: Request, pk: str | None = None) -> Response:
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["new_status"]
        allowed = {
            Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
            Order.Status.CONFIRMED: {Order.Status.SHIPPED, Order.Status.CANCELLED},
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
            {"status": e.status, "timestamp": e.timestamp, "location": e.location} for e in events
        ]
        return Response(
            {"orderId": str(order.id), "currentStatus": order.status, "trackingEvents": data},
        )
