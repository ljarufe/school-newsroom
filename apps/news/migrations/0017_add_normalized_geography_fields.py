import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("geography", "0002_load_ubigeo_2025_12_31"),
        ("news", "0016_public_news_search_infrastructure"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="geo_department",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="geography.department",
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="geo_district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="geography.district",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="coverage_geo_department",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="geography.department",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="coverage_geo_district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="geography.district",
            ),
        ),
    ]
