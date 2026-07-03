from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import DetailView, ListView

from .models import Brand, Category, Drop, Product, ProductVariant


class CatalogView(ListView):
    template_name = "catalog/list.html"
    context_object_name = "products"
    paginate_by = 18

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category", "drop")
            .prefetch_related("images", "variants")
        )

        brand_slug = self.request.GET.get("brand")
        if brand_slug:
            qs = qs.filter(brand__slug=brand_slug)

        brand_filters = self.request.GET.getlist("brand_filter")
        if brand_filters:
            qs = qs.filter(brand__slug__in=brand_filters)

        categories = self.request.GET.getlist("category")
        if categories:
            qs = qs.filter(category__slug__in=categories)

        genders = self.request.GET.getlist("gender")
        if genders:
            qs = qs.filter(gender__in=genders)

        price_min = self.request.GET.get("price_min")
        price_max = self.request.GET.get("price_max")
        if price_min:
            try:
                qs = qs.filter(base_price__gte=float(price_min))
            except (ValueError, TypeError):
                pass
        if price_max:
            try:
                qs = qs.filter(base_price__lte=float(price_max))
            except (ValueError, TypeError):
                pass

        drops = self.request.GET.get("drops")
        if drops:
            qs = qs.filter(drop__isnull=False)

        sort = self.request.GET.get("sort", "-created_at")
        allowed_sorts = {
            "-created_at": "-created_at",
            "price": "base_price",
            "-price": "-base_price",
            "name": "name",
        }
        qs = qs.order_by(allowed_sorts.get(sort, "-created_at"))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["brands"] = Brand.objects.filter(is_active=True).annotate(
            product_count=Count("products", filter=Q(products__is_active=True))
        ).order_by("name")

        ctx["categories"] = (
            Category.objects.filter(parent__isnull=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order")
        )

        brand_slug = self.request.GET.get("brand")
        ctx["active_brand"] = Brand.objects.filter(slug=brand_slug).first() if brand_slug else None

        ctx["active_categories"] = self.request.GET.getlist("category")
        ctx["active_genders"] = self.request.GET.getlist("gender")
        ctx["active_brand_filters"] = self.request.GET.getlist("brand_filter")
        brand_filter_initial = 10
        ctx["brand_filter_initial"] = brand_filter_initial
        ctx["brands_extra_count"] = max(0, ctx["brands"].count() - brand_filter_initial)

        ctx["latest_drop"] = Drop.objects.filter(is_live=True).order_by("-number").first()
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = "catalog/detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category", "drop")
            .prefetch_related(
                "images",
                "variants",
                "variants__color",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object

        variants = product.variants.filter(is_available=True).select_related("color").order_by("size")
        ctx["variants"] = variants

        similar = (
            Product.objects.filter(
                is_active=True,
                brand=product.brand,
            )
            .exclude(pk=product.pk)
            .select_related("brand")
            .prefetch_related("images")[:4]
        )
        if similar.count() < 4:
            similar = list(similar) + list(
                Product.objects.filter(
                    is_active=True,
                    category=product.category,
                )
                .exclude(pk=product.pk)
                .exclude(pk__in=[p.pk for p in similar])
                .select_related("brand")
                .prefetch_related("images")[: 4 - similar.count()]
            )
        ctx["similar_products"] = similar

        if self.request.user.is_authenticated:
            from src.accounts.models import WishlistItem

            in_wishlist = WishlistItem.objects.filter(
                user=self.request.user,
                variant__product=product,
            ).exists()
            product._in_wishlist = in_wishlist
        else:
            product._in_wishlist = False

        return ctx
