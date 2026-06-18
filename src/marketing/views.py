from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.views import View

from .models import DropNotification, NewsletterSubscriber


class NewsletterSubscribeView(View):
    def post(self, request):
        email = request.POST.get("email", "").strip().lower()
        website = request.POST.get("website", "")

        if website:
            if request.htmx:
                return HttpResponse(
                    '<div class="nl-form"><p>Дякуємо за підписку!</p></div>'
                )
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if not email or "@" not in email:
            if request.htmx:
                return HttpResponse(
                    '<div class="nl-form"><p class="nl-error">Введіть коректний email.</p></div>',
                    status=422,
                )
            messages.error(request, "Введіть коректний email.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        _, created = NewsletterSubscriber.objects.get_or_create(email=email)

        if request.htmx:
            if created:
                return HttpResponse(
                    '<div class="nl-form nl-form--success">'
                    "<p>Дякуємо! Ви підписались на розсилку DropRoom.</p>"
                    "<span class='nl-note'>Перший лист — за 24 год до наступного дропу.</span>"
                    "</div>"
                )
            return HttpResponse(
                '<div class="nl-form">'
                "<p>Ви вже підписані на наш дроп-лист.</p>"
                "</div>"
            )

        if created:
            messages.success(request, "Ви підписались на розсилку DropRoom!")
        else:
            messages.info(request, "Ви вже підписані на наш дроп-лист.")
        return redirect(request.META.get("HTTP_REFERER", "/"))


class DropNotifyView(View):
    def post(self, request):
        email = request.POST.get("email", "").strip().lower()
        drop_id = request.POST.get("drop_id")

        if not email or "@" not in email:
            if request.htmx:
                return HttpResponse(
                    '<p class="form-error">Введіть коректний email.</p>', status=422
                )
            messages.error(request, "Введіть коректний email.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        from src.catalog.models import Drop

        if not drop_id:
            drop = Drop.objects.order_by("-number").first()
        else:
            try:
                drop = Drop.objects.get(pk=drop_id)
            except Drop.DoesNotExist:
                drop = Drop.objects.order_by("-number").first()

        if not drop:
            if request.htmx:
                return HttpResponse("<p>Скоро буде новий дроп — підпишіться на розсилку!</p>")
            messages.info(request, "Поки немає активних дропів. Підпишіться на розсилку!")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        DropNotification.objects.get_or_create(email=email, drop=drop)

        if request.htmx:
            return HttpResponse(
                "<p>Ми повідомимо вас, коли дроп стане доступним!</p>"
            )
        messages.success(request, "Ми повідомимо вас про наступний дроп!")
        return redirect(request.META.get("HTTP_REFERER", "/"))
