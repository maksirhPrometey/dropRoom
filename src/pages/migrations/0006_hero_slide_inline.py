from django.db import migrations, models
import django.db.models.deletion


def attach_slides_to_home(apps, schema_editor):
    HomePage = apps.get_model("pages", "HomePage")
    HeroSlideImage = apps.get_model("pages", "HeroSlideImage")

    home, _ = HomePage.objects.get_or_create(pk=1)

    for slide in HeroSlideImage.objects.all():
        slide.page_id = home.pk
        slide.save(update_fields=["page_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0005_hero_slide_m2m"),
    ]

    operations = [
        migrations.AddField(
            model_name="heroslideimage",
            name="page",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hero_slides",
                to="pages.homepage",
            ),
        ),
        migrations.RunPython(attach_slides_to_home, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="homepage",
            name="hero_slide_images",
        ),
        migrations.AlterField(
            model_name="heroslideimage",
            name="page",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hero_slides",
                to="pages.homepage",
            ),
        ),
        migrations.AlterField(
            model_name="heroslideimage",
            name="image",
            field=models.ImageField(
                upload_to="pages/home/hero/",
                verbose_name="Фото",
            ),
        ),
        migrations.AlterField(
            model_name="heroslideimage",
            name="sort_order",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="№"),
        ),
        migrations.AlterModelOptions(
            name="heroslideimage",
            options={
                "ordering": ["sort_order", "pk"],
                "verbose_name": "Фото слайдера",
                "verbose_name_plural": "Фото слайдера",
            },
        ),
    ]
