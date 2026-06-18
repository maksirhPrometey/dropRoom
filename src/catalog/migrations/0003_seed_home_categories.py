from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")

    defaults = [
        {
            "name": "Sneakers",
            "slug": "sneakers",
            "sort_order": 1,
            "show_on_home": True,
            "home_layout": "big",
            "home_variant": "dark",
            "home_tag": "Featured",
            "is_featured": True,
        },
        {
            "name": "Outerwear",
            "slug": "outerwear",
            "sort_order": 2,
            "show_on_home": True,
            "home_layout": "wide",
        },
        {
            "name": "Knitwear",
            "slug": "knitwear",
            "sort_order": 3,
            "show_on_home": True,
        },
        {
            "name": "Denim",
            "slug": "denim",
            "sort_order": 4,
            "show_on_home": True,
        },
        {
            "name": "Accessories",
            "slug": "accessories",
            "sort_order": 5,
            "show_on_home": True,
            "home_layout": "wide",
        },
        {
            "name": "Loungewear",
            "slug": "loungewear",
            "sort_order": 6,
            "show_on_home": True,
            "home_tag": "New",
        },
    ]

    for data in defaults:
        Category.objects.update_or_create(slug=data["slug"], defaults=data)


def unseed(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(
        slug__in=[
            "sneakers",
            "outerwear",
            "knitwear",
            "denim",
            "accessories",
            "loungewear",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_category_home_fields"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed),
    ]
