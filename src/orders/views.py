import json
import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from .models import Cart, CartItem, Order, OrderItem, PromoCode
from .utils import get_or_create_cart, merge_carts

logger = logging.getLogger("src")


def _cart_context(request, cart=None):
    if cart is None:
        cart = get_or_create_cart(request)
    items = cart.items.select_related(
        "variant__product__brand",
        "variant__product__category",
        "variant__color",
    ).prefetch_related("variant__product__images")

    for item in items:
        item.unit_price = item.variant.price
        item.total_price = item.variant.price * item.quantity

    cart.subtotal = cart.get_subtotal()
    cart.discount_amount = cart.get_discount()
    cart.total = cart.get_total()
    cart.total_items = sum(i.quantity for i in items)

    return cart, items


class CartView(TemplateView):
    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cart, items = _cart_context(self.request)
        ctx["cart"] = cart
        ctx["cart_items"] = items

        if self.request.user.is_authenticated:
            from src.accounts.models import WishlistItem

            wishlist_qs = (
                WishlistItem.objects.filter(user=self.request.user)
                .select_related("variant__product__brand")
                .prefetch_related("variant__product__images")[:4]
            )
            ctx["wishlist_items"] = list(wishlist_qs)
        return ctx


class CartCountView(View):
    def get(self, request):
        cart = get_or_create_cart(request)
        count = cart.get_item_count()
        return render(request, "partials/cart_count.html", {"cart_count": count})


class CartAddView(View):
    def post(self, request):
        from src.catalog.models import ProductVariant

        variant_id = request.POST.get("variant_id")
        qty = max(1, int(request.POST.get("quantity", 1)))

        variant = get_object_or_404(ProductVariant, pk=variant_id, is_available=True)
        cart = get_or_create_cart(request)

        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, defaults={"quantity": qty}
        )
        if not created:
            item.quantity = min(item.quantity + qty, 10)
            item.save(update_fields=["quantity"])

        cart_count = cart.get_item_count()
        if request.htmx:
            response = render(
                request,
                "partials/cart_add_response.html",
                {"cart_count": cart_count},
            )
            response["HX-Trigger"] = json.dumps(
                {"cartAdded": {"productName": variant.product.name}}
            )
            return response
        messages.success(request, f"{variant.product.name} додано до кошика.")
        return redirect("orders:cart")


class CartUpdateView(View):
    def post(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id)
        qty = max(0, int(request.POST.get("quantity", 1)))
        if qty == 0:
            cart = item.cart
            item.delete()
        else:
            item.quantity = min(qty, 10)
            item.save(update_fields=["quantity"])
            cart = item.cart

        if request.htmx:
            cart_obj, items = _cart_context(request, cart)
            return render(
                request,
                "orders/cart.html",
                {"cart": cart_obj, "cart_items": items},
            )
        return redirect("orders:cart")


class CartRemoveView(View):
    def post(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id)
        cart = item.cart
        item.delete()

        if request.htmx:
            return HttpResponse("")
        return redirect("orders:cart")

    delete = post


class CartPromoView(View):
    def post(self, request):
        action = request.POST.get("action", "apply")
        cart = get_or_create_cart(request)
        error = None

        if action == "remove":
            cart.promo = None
            cart.save(update_fields=["promo"])
        else:
            code = request.POST.get("code", "").strip().upper()
            try:
                promo = PromoCode.objects.get(code=code, is_active=True)
                if promo.is_valid(cart.get_subtotal()):
                    cart.promo = promo
                    cart.save(update_fields=["promo"])
                else:
                    error = "Промокод недійсний або не відповідає умовам."
            except PromoCode.DoesNotExist:
                error = "Промокод не знайдено."

        cart.subtotal = cart.get_subtotal()
        cart.discount_amount = cart.get_discount()
        cart.total = cart.get_total()
        cart.total_items = cart.get_item_count()

        if request.htmx:
            return render(
                request,
                "orders/cart.html",
                {
                    "cart": cart,
                    "cart_items": cart.items.select_related("variant__product__brand"),
                    "promo_error": error,
                },
            )
        if error:
            messages.error(request, error)
        return redirect("orders:cart")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CheckoutView(View):
    template_name = "orders/checkout.html"

    def _checkout_totals(self, cart, delivery_method="nova_poshta"):
        from .forms import CheckoutForm

        subtotal = cart.get_subtotal()
        discount = cart.get_discount()
        delivery_cost = CheckoutForm.delivery_cost_for(subtotal, delivery_method)
        order_total = CheckoutForm.order_total_for(subtotal, discount, delivery_method)
        return subtotal, discount, delivery_cost, order_total

    def _ctx(self, request, form=None):
        cart, items = _cart_context(request)
        from .forms import CheckoutForm

        form = form or CheckoutForm(user=request.user)
        delivery_method = "nova_poshta"
        if form.is_bound and form.data.get("delivery_method"):
            delivery_method = form.data.get("delivery_method")
        elif form.is_bound and form.is_valid():
            delivery_method = form.cleaned_data.get("delivery_method", delivery_method)

        subtotal, discount, delivery_cost, order_total = self._checkout_totals(
            cart, delivery_method
        )

        return {
            "cart": cart,
            "cart_items": items,
            "form": form,
            "delivery_cost": delivery_cost,
            "order_total": order_total,
            "checkout_subtotal": subtotal,
            "checkout_discount": discount,
        }

    def get(self, request):
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            messages.info(request, "Кошик порожній — додайте товари перед оформленням.")
            return redirect("orders:cart")
        return render(request, self.template_name, self._ctx(request))

    def post(self, request):
        from django.db import transaction

        from .forms import CheckoutForm

        cart = get_or_create_cart(request)
        if not cart.items.exists():
            messages.info(request, "Кошик порожній — додайте товари перед оформленням.")
            return redirect("orders:cart")

        form = CheckoutForm(request.POST, user=request.user)
        subtotal = cart.get_subtotal()
        discount = cart.get_discount()
        form.bind_cart_totals(subtotal, discount)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {**self._ctx(request, form)},
            )

        unavailable = [
            item
            for item in cart.items.select_related("variant__product")
            if not item.variant.in_stock
        ]
        if unavailable:
            names = ", ".join(i.variant.product.name for i in unavailable[:3])
            form.add_error(
                None,
                f"Деякі товари недоступні: {names}. Оновіть кошик і спробуйте знову.",
            )
            return render(
                request,
                self.template_name,
                {**self._ctx(request, form)},
            )

        with transaction.atomic():
            order = self._create_order(request, cart, form)
            cart.items.all().delete()
            cart.promo = None
            cart.save(update_fields=["promo"])
        messages.success(request, f"Замовлення #{order.pk} успішно оформлено!")
        return redirect("orders:success", pk=order.pk)

    def _create_order(self, request, cart, form):
        subtotal = cart.get_subtotal()
        discount = cart.get_discount()
        delivery_method = form.cleaned_data["delivery_method"]
        delivery_cost = form.delivery_cost()
        total = form.order_total()

        delivery_info = form.cleaned_data.get("delivery_address", "")
        comment = form.cleaned_data.get("comment", "")
        notes_parts = [
            f"Доставка: {form.delivery_label()}",
            f"Адреса: {delivery_info}",
        ]
        if comment:
            notes_parts.append(f"Коментар: {comment}")
        notes = "\n".join(notes_parts)

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            phone=form.cleaned_data["phone"],
            email=form.cleaned_data.get("email", ""),
            promo=cart.promo,
            payment_method=form.cleaned_data["payment_method"],
            subtotal=subtotal,
            discount_amount=discount,
            delivery_cost=delivery_cost,
            total=total,
            notes=notes,
        )

        for item in cart.items.select_related("variant__product__brand"):
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                name_snapshot=item.variant.product.name,
                brand_snapshot=item.variant.product.brand.name,
                price_snapshot=item.variant.price,
                quantity=item.quantity,
            )

        if cart.promo:
            cart.promo.uses_count += 1
            cart.promo.save(update_fields=["uses_count"])

        profile = getattr(request.user, "profile", None)
        if profile and not profile.phone:
            profile.phone = form.cleaned_data["phone"]
            profile.save(update_fields=["phone"])

        return order


class OrderSuccessView(TemplateView):
    template_name = "orders/success.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["order"] = get_object_or_404(
            Order.objects.prefetch_related("items"), pk=kwargs["pk"]
        )
        return ctx
