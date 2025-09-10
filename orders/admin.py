from django.contrib import admin

# Register your models here.
from .models import Cart, CartItem, Order, OrderItem, OrderTracking

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "created_at")

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product_id", "quantity", "price")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "status", "total_amount", "currency", "created_at")
    search_fields = ("id", "user_id")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product_id", "quantity", "subtotal")

@admin.register(OrderTracking)
class OrderTrackingAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "status", "timestamp", "location")

