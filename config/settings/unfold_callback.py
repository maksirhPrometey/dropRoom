def environment_callback(request):
    from django.conf import settings

    if settings.DEBUG:
        return ["Розробка", "warning"]
    return ["Продакшн", "success"]
