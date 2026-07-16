from django import forms
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.blocks.stream_block import StreamBlockValidationError

from .access import FULL_EDITOR_PERMISSION
from .image_metadata import REQUIRED_METADATA_PARTS, effective_text


class MvpAccessPageAdminForm(WagtailAdminPageForm):
    """Apply the MVP field boundary and protect child relations server-side."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.for_user and not self.for_user.has_perm(FULL_EDITOR_PERMISSION):
            self.formsets.clear()

    def save(self, commit=True):
        if (
            self.show_comments_toggle
            and self.subscription
            and "comment_notifications" not in self.cleaned_data
        ):
            self.cleaned_data["comment_notifications"] = (
                self.subscription.comment_notifications
            )
        return super().save(commit=commit)


class NewsPageAdminForm(MvpAccessPageAdminForm):
    class Media:
        js = ["news/js/caption_alt_sync.js"]

    BODY_BLOCK_ERROR = "Revisa los bloques marcados con errores."
    PUBLIC_CREDIT_REQUIRED_ERROR = (
        "Añade al menos una firma pública antes de publicar la noticia."
    )
    MINOR_AUTHORIZATION_REQUIRED_ERROR = (
        "Confirma que se verificaron las autorizaciones requeridas para los "
        "menores identificables antes de publicar la noticia."
    )
    IMAGE_CONTEXTS = (
        ("featured_image", "imagen destacada"),
        ("og_image", "imagen para redes sociales"),
    )

    def add_error(self, field, error):
        if field == "body" and isinstance(error, StreamBlockValidationError):
            error.message = self.BODY_BLOCK_ERROR
        super().add_error(field, error)

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

        self._validate_contextual_image_metadata(cleaned_data)

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

    def _validate_contextual_image_metadata(self, cleaned_data) -> None:
        for image_field, context_label in self.IMAGE_CONTEXTS:
            if not cleaned_data.get(image_field):
                continue
            for metadata_part, metadata_label in REQUIRED_METADATA_PARTS:
                field_name = f"{image_field}_{metadata_part}"
                if effective_text(cleaned_data.get(field_name)):
                    continue
                self.add_error(
                    field_name,
                    forms.ValidationError(
                        f"Completa el {metadata_label} de la {context_label} "
                        "antes de publicar la noticia.",
                        code=f"missing_{field_name}",
                    ),
                )

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
