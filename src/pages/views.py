from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import FormView, TemplateView

from .forms import ContactForm
from .hero_slides import build_hero_slides
from .models import ContactsPage, HomePage, StoryPage


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Count, Q

        from src.catalog.models import Brand, Category, Drop, Product
        from src.marketing.models import NewsletterSubscriber

        home_page = HomePage.load()
        ctx["home_page"] = home_page
        ctx["stat_blocks"] = home_page.stat_blocks.all()
        ctx["hero_slides"] = build_hero_slides(
            home_page.hero_slides.order_by("sort_order", "pk")
        )
        ctx["hero_slider_autoplay_ms"] = home_page.hero_slider_autoplay_seconds * 1000
        ctx["hero_slider_autoplay_enabled"] = home_page.hero_slider_autoplay_enabled

        ctx["latest_drop"] = Drop.objects.order_by("-number").first()
        ctx["brands"] = Brand.objects.filter(is_active=True).order_by("name")
        ctx["brands_count"] = ctx["brands"].count()

        ctx["categories"] = (
            Category.objects.filter(parent__isnull=True, show_on_home=True)
            .annotate(
                product_count=Count(
                    "products", filter=Q(products__is_active=True), distinct=True
                )
            )
            .order_by("sort_order", "name")[:6]
        )
        ctx["home_categories_count"] = ctx["categories"].count()

        product_qs = (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category")
            .prefetch_related("images", "variants")
            .order_by("-created_at")
        )
        latest_products = list(product_qs[:4])
        latest_ids = [product.pk for product in latest_products]
        ctx["latest_products"] = latest_products
        ctx["featured_products"] = product_qs.exclude(pk__in=latest_ids)[:8]
        ctx["products_count"] = Product.objects.filter(is_active=True).count()
        ctx["subscriber_count"] = NewsletterSubscriber.objects.filter(is_active=True).count()
        return ctx


class StoryView(TemplateView):
    template_name = "pages/story.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from src.catalog.models import Brand, Drop, Product

        story_page = StoryPage.load()
        ctx["story_page"] = story_page
        pillars = story_page.pillars.all()
        ctx["pillars"] = pillars
        from src.pages.templatetags.grid_tags import ideal_cols

        pillar_count = pillars.count() or 3
        ctx["pillars_grid_cols"] = ideal_cols(pillar_count, 3)
        ctx["timeline_events"] = story_page.timeline_events.all()
        ctx["team_members"] = story_page.team_members.filter(is_active=True)

        ctx["brands"] = Brand.objects.filter(is_active=True).order_by("name")
        ctx["brands_count"] = ctx["brands"].count()
        ctx["products_count"] = Product.objects.filter(is_active=True).count()

        latest_drop = Drop.objects.order_by("-number").first()
        ctx["latest_drop"] = latest_drop
        ctx["latest_drop_num"] = str(latest_drop.number).zfill(3) if latest_drop else "047"
        return ctx


class ContactsView(FormView):
    template_name = "pages/contacts.html"
    form_class = ContactForm

    def get_success_url(self):
        from django.urls import reverse
        return reverse("pages:contacts")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from src.catalog.models import Brand

        contacts_page = ContactsPage.load()
        ctx["contacts_page"] = contacts_page
        ctx["stores"] = contacts_page.stores.filter(is_active=True)
        ctx["contact_channels"] = contacts_page.channels.filter(is_active=True)
        ctx["faq_items"] = contacts_page.faq_items.filter(is_active=True)
        ctx["brands"] = Brand.objects.filter(is_active=True).order_by("name")
        return ctx

    def form_valid(self, form):
        if self.request.htmx:
            return render(
                self.request,
                "pages/contacts.html",
                {**self.get_context_data(form=form), "form_success": True},
            )
        messages.success(
            self.request, "Ваше повідомлення надіслано. Ми відповімо незабаром."
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.htmx:
            return render(
                self.request,
                "pages/contacts.html",
                self.get_context_data(form=form),
                status=422,
            )
        return super().form_invalid(form)
