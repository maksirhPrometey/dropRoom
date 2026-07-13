from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_compare_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(max_length=255, unique=True),
        ),
    ]
