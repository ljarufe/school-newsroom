from django import forms
from django.urls import reverse


class DependentDistrictWidget(forms.Widget):
    template_name = "geography/widgets/dependent_district.html"

    def __init__(self, *, department_field: str, attrs=None):
        self.department_field = department_field
        super().__init__(attrs)

    class Media:
        css = {"all": ("geography/css/dependent_district.css",)}
        js = ("geography/js/dependent_district.js",)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        code = str(getattr(value, "value", value) or "")
        selected = None
        if code:
            from .models import District

            selected = (
                District.objects.select_related("province__department")
                .filter(code=code)
                .first()
            )
        context["widget"].update(
            lookup_url=reverse("geography:district_lookup"),
            department_field_id=f"id_{self.department_field}",
            selected_name=selected.name if selected else "",
            selected_department=(selected.province.department_id if selected else ""),
        )
        return context
