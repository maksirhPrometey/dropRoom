from django.core.management.base import BaseCommand

from src.pages.hero_defaults import apply_hero_slide_copy
from src.pages.models import HomePage


class Command(BaseCommand):
    help = "Оновити текст hero-слайдів (слоган + посилання на каталог) без зміни фото."

    def handle(self, *args, **options):
        home_page = HomePage.load()
        slides = list(home_page.hero_slides.order_by("sort_order", "pk"))

        if not slides:
            self.stdout.write(self.style.WARNING("Hero-слайдів не знайдено."))
            return

        for index, slide in enumerate(slides):
            apply_hero_slide_copy(slide, index)
            slide.save(
                update_fields=[
                    "eyebrow",
                    "title_line1",
                    "title_accent",
                    "subtitle",
                    "usp_text",
                    "feature_1",
                    "feature_2",
                    "feature_3",
                    "cta_text",
                    "link",
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(f"Оновлено текст для {len(slides)} hero-слайдів.")
        )
