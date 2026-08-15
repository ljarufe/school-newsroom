import csv
from pathlib import Path

from django.db import migrations


SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "peru_ubigeo_2025-12-31.csv"
)


def load_snapshot(apps, schema_editor):
    Department = apps.get_model("geography", "Department")
    Province = apps.get_model("geography", "Province")
    District = apps.get_model("geography", "District")
    database = schema_editor.connection.alias

    departments = {}
    provinces = {}
    districts = []
    with SNAPSHOT_PATH.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            departments[row["department_code"]] = row["department_name"]
            provinces[row["province_code"]] = (
                row["province_name"],
                row["department_code"],
            )
            districts.append(
                (
                    row["district_code"],
                    row["district_name"],
                    row["province_code"],
                )
            )

    if (len(departments), len(provinces), len(districts)) != (25, 196, 1892):
        raise RuntimeError("The versioned UBIGEO snapshot has unexpected counts.")
    if departments.get("04") != "Arequipa":
        raise RuntimeError("The versioned UBIGEO snapshot lacks Arequipa code 04.")

    Department.objects.using(database).bulk_create(
        [Department(code=code, name=name) for code, name in sorted(departments.items())]
    )
    Province.objects.using(database).bulk_create(
        [
            Province(code=code, name=name, department_id=department_code)
            for code, (name, department_code) in sorted(provinces.items())
        ]
    )
    District.objects.using(database).bulk_create(
        [
            District(code=code, name=name, province_id=province_code)
            for code, name, province_code in sorted(districts)
        ]
    )


def unload_snapshot(apps, schema_editor):
    database = schema_editor.connection.alias
    apps.get_model("geography", "District").objects.using(database).all().delete()
    apps.get_model("geography", "Province").objects.using(database).all().delete()
    apps.get_model("geography", "Department").objects.using(database).all().delete()


class Migration(migrations.Migration):
    dependencies = [("geography", "0001_initial")]

    operations = [migrations.RunPython(load_snapshot, unload_snapshot)]
