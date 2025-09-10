from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem


class ProductSearchResultSerializer(serializers.Serializer):
    productId = serializers.CharField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    availability = serializers.CharField()


class CartItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["id", "cart", "product_id", "quantity", "price"]
        read_only_fields = ["id"]

    def validate_quantity(self, v):
        if v < 1:
            raise serializers.ValidationError("quantity must be >= 1")
        return v


class CartSerializer(serializers.ModelSerializer):
    items = CartItemCreateSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user_id", "created_at", "updated_at", "items", "total"]

    def get_total(self, obj):
        return obj.total_amount()


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "quantity", "price", "subtotal"]


class OrderCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    items = OrderItemSerializer(many=True)
    address_id = serializers.CharField()
    payment_method_id = serializers.CharField()
    currency = serializers.CharField(default="USD")
    idempotency_key = serializers.CharField(required=False, allow_null=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        return items


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    tracking_events = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "user_id", "status", "total_amount", "currency", "address_id",
                  "payment_method_id", "payment_transaction_id", "created_at", "items", "tracking_events"]

    def get_tracking_events(self, order):
        events = order.tracking_events.order_by("timestamp").all()
        return [{"status": e.status, "timestamp": e.timestamp, "location": e.location} for e in events]


class OrderStatusUpdateSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(choices=Order.Status.choices)
