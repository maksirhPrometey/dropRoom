from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.CatalogView.as_view(), name="list"),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="detail"),
]
