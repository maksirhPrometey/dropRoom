from django.test import SimpleTestCase

from src.pages.hero_defaults import apply_hero_slide_copy, hero_slide_copy_for_index


class HeroDefaultsTests(SimpleTestCase):
    def test_copy_links_to_catalog(self):
        copy = hero_slide_copy_for_index(0)
        self.assertEqual(copy["link"], "/catalog/")
        self.assertEqual(copy["cta_text"], "До каталогу")
        self.assertNotIn("товар", copy["cta_text"].lower())

    def test_apply_sets_slogan_not_product_name(self):
        class FakeSlide:
            eyebrow = title_line1 = title_accent = subtitle = ""
            usp_text = feature_1 = feature_2 = feature_3 = ""
            cta_text = link = ""

        slide = FakeSlide()
        apply_hero_slide_copy(slide, 0)
        self.assertEqual(slide.title_line1, "СТИЛЬ,")
        self.assertEqual(slide.title_accent, "ЩО В ТЕБЕ.")
