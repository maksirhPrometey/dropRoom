from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("subscribe/", views.NewsletterSubscribeView.as_view(), name="subscribe"),
    path("drop-notify/", views.DropNotifyView.as_view(), name="drop_notify"),
]
