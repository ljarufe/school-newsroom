from django.db import models
from django.db.models import Q


class Department(models.Model):
    code = models.CharField("Código UBIGEO", max_length=2, primary_key=True)
    name = models.CharField("Nombre", max_length=100)
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ("name", "code")
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        constraints = [
            models.CheckConstraint(
                condition=~Q(name=""),
                name="geography_department_name_not_empty",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Province(models.Model):
    code = models.CharField("Código UBIGEO", max_length=4, primary_key=True)
    name = models.CharField("Nombre", max_length=100)
    department = models.ForeignKey(
        Department,
        verbose_name="Departamento",
        on_delete=models.PROTECT,
        related_name="provinces",
    )
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ("department_id", "name", "code")
        verbose_name = "Provincia"
        verbose_name_plural = "Provincias"
        constraints = [
            models.CheckConstraint(
                condition=~Q(name=""),
                name="geography_province_name_not_empty",
            )
        ]

    def __str__(self) -> str:
        return self.name


class District(models.Model):
    code = models.CharField("Código UBIGEO", max_length=6, primary_key=True)
    name = models.CharField("Nombre", max_length=100)
    province = models.ForeignKey(
        Province,
        verbose_name="Provincia",
        on_delete=models.PROTECT,
        related_name="districts",
    )
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ("province__department_id", "name", "code")
        verbose_name = "Distrito"
        verbose_name_plural = "Distritos"
        constraints = [
            models.CheckConstraint(
                condition=~Q(name=""),
                name="geography_district_name_not_empty",
            )
        ]

    def __str__(self) -> str:
        return self.name
