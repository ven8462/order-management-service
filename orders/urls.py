from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartViewSet, OrderViewSet, product_search

router = DefaultRouter()
# cart -- a custom route for adding items
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = [
    path("products/search", product_search, name="product-search"),
    path("", include(router.urls)),
]
