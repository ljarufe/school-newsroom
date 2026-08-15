from django import forms

from apps.geography.forms import configure_geography_fields
from apps.geography.widgets import DependentDistrictWidget

from .models import School


class SchoolAdminForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ("name", "department", "district")
        widgets = {
            "district": DependentDistrictWidget(department_field="department"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configure_geography_fields(
            self,
            department_field="department",
            district_field="district",
        )
