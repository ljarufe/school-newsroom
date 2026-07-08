from django import forms
from wagtail.admin.forms import WagtailAdminPageForm


class NewsPageAdminForm(WagtailAdminPageForm):
    PUBLIC_CREDIT_REQUIRED_ERROR = (
        "Añade al menos una firma pública antes de publicar la noticia."
    )
    MINOR_AUTHORIZATION_REQUIRED_ERROR = (
        "Confirma que se verificaron las autorizaciones requeridas para los "
        "menores identificables antes de publicar la noticia."
    )

    def clean(self):
        cleaned_data = super().clean()

        if self.is_deferred_validation:
            return cleaned_data

        if not self._has_effective_public_credit():
            self.add_error(
                None,
                forms.ValidationError(
                    self.PUBLIC_CREDIT_REQUIRED_ERROR,
                    code="missing_public_credit",
                ),
            )

        if cleaned_data.get("contains_identifiable_minors") and not cleaned_data.get(
            "minor_publication_authorizations_verified"
        ):
            self.add_error(
                "minor_publication_authorizations_verified",
                forms.ValidationError(
                    self.MINOR_AUTHORIZATION_REQUIRED_ERROR,
                    code="missing_minor_publication_authorization",
                ),
            )

        return cleaned_data

    def _has_effective_public_credit(self) -> bool:
        formset = self.formsets.get("public_credits")
        if formset is None:
            return self.instance.public_credits.filter(display_name__gt="").exists()

        if formset.is_bound:
            formset.is_valid()
            for form in formset.forms:
                if formset.can_delete and formset._should_delete_form(form):
                    continue
                display_name = form.cleaned_data.get("display_name", "")
                if display_name.strip():
                    return True
            return False

        return any(
            public_credit.display_name.strip()
            for public_credit in self.instance.public_credits.all()
        )
