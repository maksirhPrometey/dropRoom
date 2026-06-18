from django.db import migrations


def seed_hero_cards(apps, schema_editor):
    HomePage = apps.get_model("pages", "HomePage")
    HeroStripCard = apps.get_model("pages", "HeroStripCard")

    page, _ = HomePage.objects.get_or_create(pk=1)
    if HeroStripCard.objects.filter(page=page).exists():
        return

    HeroStripCard.objects.bulk_create(
        [
            HeroStripCard(
                page=page,
                layout="category",
                sort_order=1,
                label="FIGURE · COAT · STUDIO",
                title="Outerwear /<br>Spring Layers",
                meta="42 позиції\n15 брендів",
                link="/catalog/",
            ),
            HeroStripCard(
                page=page,
                layout="drop",
                sort_order=2,
                use_live_drop=True,
                drop_label="— Drop No.",
                title="Drop 047",
                link="/catalog/?drops=true",
            ),
            HeroStripCard(
                page=page,
                layout="category",
                sort_order=3,
                label="SNEAKERS · OUTDOOR · MACRO",
                title="Footwear /<br>Running Floor",
                meta="94 пари\n8 брендів",
                link="/catalog/",
            ),
        ]
    )


def unseed(apps, schema_editor):
    HeroStripCard = apps.get_model("pages", "HeroStripCard")
    HeroStripCard.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0002_hero_strip_cards"),
    ]

    operations = [
        migrations.RunPython(seed_hero_cards, unseed),
    ]
