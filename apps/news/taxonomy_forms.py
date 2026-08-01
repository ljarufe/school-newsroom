from django import forms

from .models import NewsSection


class NewsSubsectionAdminForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        label="Sección principal",
        queryset=NewsSection.objects.none(),
        required=True,
        empty_label="Selecciona una sección principal",
        error_messages={
            "required": "Selecciona una sección principal.",
            "invalid_choice": "Selecciona una sección principal válida.",
        },
    )

    class Meta:
        model = NewsSection
        fields = ("name", "slug", "parent", "sort_order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = NewsSection.objects.filter(
            parent__isnull=True
        ).order_by("sort_order", "name", "pk")
