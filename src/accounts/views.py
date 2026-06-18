from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import RegisterForm
from .models import WishlistItem


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm

    def get_success_url(self):
        from django.urls import reverse
        return reverse("pages:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("pages:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)

        from src.orders.utils import merge_carts
        session_key = self.request.session.session_key or ""
        merge_carts(user, session_key)

        messages.success(self.request, f"Ласкаво просимо, {user.first_name or user.username}!")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = "/accounts/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["profile"] = getattr(user, "profile", None)
        orders_qs = user.orders.select_related("promo").prefetch_related("items")
        ctx["orders_count"] = orders_qs.count()
        ctx["orders"] = orders_qs.order_by("-created_at")[:10]
        ctx["addresses"] = user.addresses.all()
        ctx["wishlist_count"] = WishlistItem.objects.filter(user=user).count()
        return ctx


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/wishlist.html"
    login_url = "/accounts/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["profile"] = getattr(user, "profile", None)
        wishlist_qs = WishlistItem.objects.filter(user=user)
        ctx["wishlist_count"] = wishlist_qs.count()
        ctx["orders_count"] = user.orders.count()
        ctx["wishlist_items"] = wishlist_qs.select_related(
            "variant__product__brand", "variant__product__category"
        ).prefetch_related("variant__product__images")
        return ctx


class WishlistToggleView(View):
    def post(self, request, product_id):
        if not request.user.is_authenticated:
            if request.htmx:
                return HttpResponse(
                    '<button class="wishlist" hx-post="/accounts/wishlist/toggle/{product_id}/" hx-swap="outerHTML">'
                    '<svg viewBox="0 0 14 14" width="14" height="14" stroke="currentColor" fill="none" stroke-width="1.3">'
                    '<path d="M7 12.2S1.5 8.6 1.5 5a3 3 0 015.5-1.7A3 3 0 0112.5 5c0 3.6-5.5 7.2-5.5 7.2z"/>'
                    "</svg></button>"
                )
            return redirect("accounts:login")

        from src.catalog.models import Product

        product = get_object_or_404(Product, pk=product_id, is_active=True)
        existing = WishlistItem.objects.filter(
            user=request.user, variant__product=product
        )
        if existing.exists():
            existing.delete()
            in_wishlist = False
        else:
            variant = product.variants.filter(is_available=True).order_by("size").first()
            if variant:
                WishlistItem.objects.create(user=request.user, variant=variant)
                in_wishlist = True
            else:
                in_wishlist = False

        if request.htmx:
            from django.middleware.csrf import get_token
            fill = "var(--ink)" if in_wishlist else "none"
            label = "В обраному" if in_wishlist else "Додати до обраного"
            csrf = get_token(request)
            path = request.path
            return HttpResponse(
                f'<button class="wishlist-btn" hx-post="{path}" hx-swap="outerHTML">'
                f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">'
                f'<svg viewBox="0 0 14 14" width="14" height="14" stroke="currentColor" fill="{fill}" stroke-width="1.3">'
                f'<path d="M7 12.2S1.5 8.6 1.5 5a3 3 0 015.5-1.7A3 3 0 0112.5 5c0 3.6-5.5 7.2-5.5 7.2z"/>'
                f"</svg>{label}</button>"
            )
        return redirect(request.META.get("HTTP_REFERER", "catalog:list"))
