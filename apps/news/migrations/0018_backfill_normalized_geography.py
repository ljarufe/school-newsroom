from django.db import migrations


def backfill_arequipa(apps, schema_editor):
    Department = apps.get_model("geography", "Department")
    School = apps.get_model("news", "School")
    NewsPage = apps.get_model("news", "NewsPage")
    database = schema_editor.connection.alias

    if not Department.objects.using(database).filter(code="04").exists():
        raise RuntimeError("Cannot backfill geography: Department 04 is absent.")
    School.objects.using(database).update(
        geo_department_id="04",
        geo_district_id=None,
    )
    NewsPage.objects.using(database).update(
        coverage_geo_department_id="04",
        coverage_geo_district_id=None,
    )


class Migration(migrations.Migration):
    dependencies = [("news", "0017_add_normalized_geography_fields")]

    operations = [migrations.RunPython(backfill_arequipa, migrations.RunPython.noop)]
