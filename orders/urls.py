from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import product_search, CartViewSet, OrderViewSet

router = DefaultRouter()
# cart -- a custom route for adding items
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = [
    path("products/search", product_search, name="product-search"),
    path("", include(router.urls)),
]
