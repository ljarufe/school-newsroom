from django import forms
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.blocks.stream_block import StreamBlockValidationError

from .access import FULL_EDITOR_PERMISSION
from .image_metadata import REQUIRED_METADATA_PARTS, effective_text
from .widgets import TaxonomyTreeWidget


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
    taxonomy_sections = forms.MultipleChoiceField(
        label="Secciones y subsecciones",
        help_text=(
            "Selecciona una o varias secciones o subsecciones. Puedes elegir una "
            "subsección sin seleccionar también su sección principal."
        ),
        required=False,
        choices=(),
        widget=TaxonomyTreeWidget,
    )

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
    TAXONOMY_REQUIRED_ERROR = (
        "Selecciona al menos una sección o subsección antes de publicar la noticia."
    )
    IMAGE_CONTEXTS = (
        ("featured_image", "imagen destacada"),
        ("og_image", "imagen para redes sociales"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("taxonomy_sections")
        if field is None:
            return

        from .models import NewsSection

        sections = list(NewsSection.objects.select_related("parent"))
        sections.sort(
            key=lambda section: (
                (section.parent or section).sort_order,
                (section.parent or section).name.casefold(),
                (section.parent or section).pk,
                0 if section.parent_id is None else 1,
                section.sort_order,
                section.name.casefold(),
                section.pk,
            )
        )
        field.choices = [(str(section.pk), section.name) for section in sections]
        field.widget.sections = sections
        if not self.is_bound:
            self.initial["taxonomy_sections"] = [
                str(section_id)
                for section_id in self.instance.section_assignments.values_list(
                    "section_id", flat=True
                )
            ]

    def add_error(self, field, error):
        if field == "body" and isinstance(error, StreamBlockValidationError):
            error.message = self.BODY_BLOCK_ERROR
        super().add_error(field, error)

    def clean(self):
        cleaned_data = super().clean()

        if (
            "taxonomy_sections" in self.fields
            and "taxonomy_sections" not in self.errors
        ):
            self._sync_taxonomy_assignments(cleaned_data.get("taxonomy_sections", []))

        if self.is_deferred_validation:
            return cleaned_data

        if not self._has_effective_taxonomy(cleaned_data):
            target_field = (
                "taxonomy_sections" if "taxonomy_sections" in self.fields else None
            )
            self.add_error(
                target_field,
                forms.ValidationError(
                    self.TAXONOMY_REQUIRED_ERROR,
                    code="missing_taxonomy",
                ),
            )

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

    def _sync_taxonomy_assignments(self, section_values) -> None:
        from .models import NewsPageSection, NewsSection

        section_ids = list(dict.fromkeys(int(value) for value in section_values))
        sections = NewsSection.objects.select_related("parent").in_bulk(section_ids)
        assignments = [
            NewsPageSection(page=self.instance, section=sections[section_id])
            for section_id in section_ids
            if section_id in sections
        ]
        self.instance.section_assignments.set(assignments)
        self.instance.__dict__.pop("taxonomy", None)

    def _has_effective_taxonomy(self, cleaned_data) -> bool:
        if "taxonomy_sections" in self.fields:
            return bool(cleaned_data.get("taxonomy_sections"))
        return bool(self.instance.section_assignments.all())

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
