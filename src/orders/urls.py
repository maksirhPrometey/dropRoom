from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.CartView.as_view(), name="cart"),
    path("count/", views.CartCountView.as_view(), name="cart_count"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("add/", views.CartAddView.as_view(), name="cart_add"),
    path("update/<int:item_id>/", views.CartUpdateView.as_view(), name="cart_update"),
    path("remove/<int:item_id>/", views.CartRemoveView.as_view(), name="cart_remove"),
    path("promo/", views.CartPromoView.as_view(), name="cart_promo"),
]
