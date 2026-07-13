from django.core.files import File
from django.core.management.base import BaseCommand
from django.db.models import Count

from src.catalog.models import Product
from src.pages.hero_defaults import apply_hero_slide_copy
from src.pages.models import HeroSlideImage, HomePage
from src.telegram_import.models import TelegramImport


class Command(BaseCommand):
    help = (
        "Активувати імпортовані з Telegram товари на сайті. "
        "Hero-банер за замовчуванням не змінюється — лише вручну в адмінці "
        "або через --hero-slides."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hero-slides",
            type=int,
            default=0,
            help="Скільки слайдів hero зібрати з товарів (0 = не чіпати, за замовч.)",
        )
        parser.add_argument(
            "--replace-hero",
            action="store_true",
            help="Видалити поточні hero-слайди перед створенням нових",
        )

    def handle(self, *args, **options):
        product_ids = TelegramImport.objects.filter(
            status=TelegramImport.STATUS_IMPORTED,
            product_id__isnull=False,
        ).values_list("product_id", flat=True)

        updated = Product.objects.filter(pk__in=product_ids).update(is_active=True)
        self.stdout.write(self.style.SUCCESS(f"Активовано товарів: {updated}"))

        hero_count = options["hero_slides"]
        if hero_count <= 0:
            return

        home_page = HomePage.load()
        if options["replace_hero"]:
            deleted, _ = home_page.hero_slides.all().delete()
            self.stdout.write(self.style.WARNING(f"Видалено hero-слайдів: {deleted}"))

        products = (
            Product.objects.filter(pk__in=product_ids, is_active=True)
            .annotate(image_count=Count("images"))
            .filter(image_count__gt=0)
            .select_related("brand")
            .prefetch_related("images")
            .order_by("-created_at")[:hero_count]
        )

        created = 0
        for sort_order, product in enumerate(products, start=1):
            primary = product.primary_image
            if not primary or not primary.image:
                continue

            slide = HeroSlideImage(
                page=home_page,
                sort_order=sort_order,
            )
            apply_hero_slide_copy(slide, sort_order - 1)
            with primary.image.open("rb") as image_file:
                slide.image.save(primary.image.name.split("/")[-1], File(image_file), save=False)
            slide.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Створено hero-слайдів: {created}"))
