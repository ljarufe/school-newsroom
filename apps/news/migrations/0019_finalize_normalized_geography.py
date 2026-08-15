import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("news", "0018_backfill_normalized_geography")]

    operations = [
        migrations.RemoveField(model_name="school", name="province"),
        migrations.RemoveField(model_name="school", name="district"),
        migrations.RemoveField(model_name="newspage", name="coverage_province"),
        migrations.RemoveField(model_name="newspage", name="coverage_district"),
        migrations.RenameField(
            model_name="school",
            old_name="geo_department",
            new_name="department",
        ),
        migrations.RenameField(
            model_name="school",
            old_name="geo_district",
            new_name="district",
        ),
        migrations.RenameField(
            model_name="newspage",
            old_name="coverage_geo_department",
            new_name="coverage_department",
        ),
        migrations.RenameField(
            model_name="newspage",
            old_name="coverage_geo_district",
            new_name="coverage_district",
        ),
        migrations.AlterField(
            model_name="school",
            name="department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schools",
                to="geography.department",
                verbose_name="Departamento",
            ),
        ),
        migrations.AlterField(
            model_name="school",
            name="district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schools",
                to="geography.district",
                verbose_name="Distrito",
            ),
        ),
        migrations.AlterField(
            model_name="newspage",
            name="coverage_department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="covered_news_pages",
                to="geography.department",
                verbose_name="Departamento",
            ),
        ),
        migrations.AlterField(
            model_name="newspage",
            name="coverage_district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="covered_news_pages",
                to="geography.district",
                verbose_name="Distrito",
            ),
        ),
    ]
