from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path(
        "wishlist/toggle/<int:product_id>/",
        views.WishlistToggleView.as_view(),
        name="wishlist_toggle",
    ),
]
