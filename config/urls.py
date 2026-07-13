from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz),
    path("admin/", admin.site.urls),
    path("", include("src.pages.urls")),
    path("catalog/", include("src.catalog.urls")),
    path("cart/", include("src.orders.urls")),
    path("accounts/", include("src.accounts.urls")),
    path("newsletter/", include("src.marketing.urls")),
    path("telegram/", include("src.telegram_import.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
