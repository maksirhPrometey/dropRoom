from django.db import migrations, models


def seed_hero_promos(apps, schema_editor):
    HomePage = apps.get_model("pages", "HomePage")
    HeroPromoItem = apps.get_model("pages", "HeroPromoItem")
    home = HomePage.objects.first()
    if not home or HeroPromoItem.objects.filter(page=home).exists():
        return
    items = [
        ("tag", "АУТЛЕТ ЦІНИ", "Брендові речі за кращими цінами", 0),
        ("percent", "ДО -50%", "Знижки на колекційні та сезонні товари", 1),
        ("clock", "ЛІМІТОВАНІ ПОЗИЦІЇ", "Унікальні речі. Поки є в наявності", 2),
    ]
    for icon, title, description, sort_order in items:
        HeroPromoItem.objects.create(
            page=home,
            icon=icon,
            title=title,
            description=description,
            sort_order=sort_order,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0007_hero_slide_admin_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="heroslideimage",
            name="cta_text",
            field=models.CharField(
                blank=True,
                help_text="Напр.: Перейти до аутлету",
                max_length=80,
                verbose_name="Текст кнопки",
            ),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="eyebrow",
            field=models.CharField(
                blank=True,
                help_text="Напр.: OUTLET — ОРИГІНАЛЬНІ БРЕНДИ",
                max_length=120,
                verbose_name="Плашка зверху",
            ),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="feature_1",
            field=models.CharField(blank=True, max_length=80, verbose_name="Перевага 1"),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="feature_2",
            field=models.CharField(blank=True, max_length=80, verbose_name="Перевага 2"),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="feature_3",
            field=models.CharField(blank=True, max_length=80, verbose_name="Перевага 3"),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="link",
            field=models.CharField(
                blank=True,
                help_text="URL або шлях (/catalog/). Порожнє — каталог.",
                max_length=255,
                verbose_name="Посилання кнопки",
            ),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="subtitle",
            field=models.CharField(blank=True, max_length=200, verbose_name="Підзаголовок"),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="title_accent",
            field=models.CharField(
                blank=True,
                help_text="Напр.: ЩО В ТЕБЕ. — виділяється кольором.",
                max_length=100,
                verbose_name="Заголовок (акцент)",
            ),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="title_line1",
            field=models.CharField(
                blank=True,
                help_text="Напр.: СТИЛЬ,",
                max_length=100,
                verbose_name="Заголовок (частина 1)",
            ),
        ),
        migrations.AddField(
            model_name="heroslideimage",
            name="usp_text",
            field=models.CharField(
                blank=True,
                help_text="Напр.: ДОСТУПНО. ВИГІДНО. ОРИГІНАЛЬНО.",
                max_length=200,
                verbose_name="Рамка USP",
            ),
        ),
        migrations.CreateModel(
            name="HeroPromoItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        choices=[
                            ("tag", "Цінник"),
                            ("percent", "Знижка"),
                            ("clock", "Ліміт"),
                        ],
                        default="tag",
                        max_length=20,
                        verbose_name="Іконка",
                    ),
                ),
                ("title", models.CharField(max_length=80, verbose_name="Заголовок")),
                ("description", models.CharField(max_length=200, verbose_name="Опис")),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Порядок"),
                ),
                (
                    "page",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="hero_promos",
                        to="pages.homepage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Промо під hero",
                "verbose_name_plural": "Промо під hero",
                "ordering": ["sort_order", "pk"],
            },
        ),
        migrations.RunPython(seed_hero_promos, migrations.RunPython.noop),
    ]
