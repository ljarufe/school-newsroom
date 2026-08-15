from django.db.models import Q

from .models import Department, District


def configure_geography_fields(
    form,
    *,
    department_field: str,
    district_field: str,
) -> None:
    department = form.fields.get(department_field)
    district = form.fields.get(district_field)
    if department is None or district is None:
        return

    instance_department = getattr(form.instance, f"{department_field}_id", None)
    instance_district = getattr(form.instance, f"{district_field}_id", None)
    department.queryset = Department.objects.filter(
        Q(is_active=True) | Q(code=instance_department)
    ).order_by("name", "code")
    district.queryset = District.objects.filter(
        Q(
            is_active=True,
            province__is_active=True,
            province__department__is_active=True,
        )
        | Q(code=instance_district)
    ).select_related("province__department")
