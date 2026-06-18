# Generated manually for category home display fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Фото для плитки на головній і в каталозі.",
                null=True,
                upload_to="categories/",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="show_on_home",
            field=models.BooleanField(
                default=False,
                help_text="Показувати в блоці «Категорії / сезону» на головній.",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="home_layout",
            field=models.CharField(
                choices=[
                    ("normal", "Звичайна"),
                    ("wide", "Широка (2 колонки)"),
                    ("big", "Велика (3 колонки)"),
                ],
                default="normal",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="home_variant",
            field=models.CharField(
                choices=[("light", "Світла"), ("dark", "Темна (білий текст)")],
                default="light",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="home_tag",
            field=models.CharField(
                blank=True,
                help_text="Плашка зверху: Featured, New тощо.",
                max_length=30,
            ),
        ),
    ]
