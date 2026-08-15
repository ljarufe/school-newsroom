import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "code",
                    models.CharField(
                        max_length=2,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Código UBIGEO",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Nombre")),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Activo"),
                ),
            ],
            options={
                "verbose_name": "Departamento",
                "verbose_name_plural": "Departamentos",
                "ordering": ("name", "code"),
            },
        ),
        migrations.CreateModel(
            name="Province",
            fields=[
                (
                    "code",
                    models.CharField(
                        max_length=4,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Código UBIGEO",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Nombre")),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Activo"),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="provinces",
                        to="geography.department",
                        verbose_name="Departamento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Provincia",
                "verbose_name_plural": "Provincias",
                "ordering": ("department_id", "name", "code"),
            },
        ),
        migrations.CreateModel(
            name="District",
            fields=[
                (
                    "code",
                    models.CharField(
                        max_length=6,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Código UBIGEO",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Nombre")),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Activo"),
                ),
                (
                    "province",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="districts",
                        to="geography.province",
                        verbose_name="Provincia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Distrito",
                "verbose_name_plural": "Distritos",
                "ordering": ("province__department_id", "name", "code"),
            },
        ),
        migrations.AddConstraint(
            model_name="department",
            constraint=models.CheckConstraint(
                condition=models.Q(("name", ""), _negated=True),
                name="geography_department_name_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="province",
            constraint=models.CheckConstraint(
                condition=models.Q(("name", ""), _negated=True),
                name="geography_province_name_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="district",
            constraint=models.CheckConstraint(
                condition=models.Q(("name", ""), _negated=True),
                name="geography_district_name_not_empty",
            ),
        ),
    ]
