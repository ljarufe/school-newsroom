from django import forms
from django.urls import reverse
from wagtail.admin.panels import FieldPanel, ObjectList, Panel
from wagtail.models import Site

from .seo import analyze_page
from .seo_metadata import build_public_metadata, served_public_url


def contextual_image_panels(image_field: str, metadata_prefix: str) -> list[Panel]:
    return [
        FieldPanel(image_field),
        FieldPanel(f"{metadata_prefix}_caption"),
        FieldPanel(f"{metadata_prefix}_alt_text"),
        FieldPanel(f"{metadata_prefix}_credit"),
    ]


class RolePermissionObjectList(ObjectList):
    """Apply a tab permission to its form fields and rendered panel."""

    def get_form_options(self):
        options = super().get_form_options()
        if not self.permission:
            return options

        field_permissions = {
            field_name: self.permission for field_name in options.get("fields", [])
        }
        field_permissions.update(options.get("field_permissions", {}))
        options["field_permissions"] = field_permissions
        return options


class SeoAssistantPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "news/admin/seo_assistant_panel.html"

        class Media:
            css = {"all": ["news/css/seo_assistant.css"]}
            js = ["news/js/seo_assistant.js"]

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            site = Site.find_for_request(self.request)
            site_hostname = site.hostname if site else ""
            metadata = build_public_metadata(self.instance, self.request)
            public_url = served_public_url(self.instance, self.request) or (
                f"/{self.instance.slug}/"
                if self.instance.slug
                else "/slug-de-la-noticia/"
            )
            preview_url = metadata.canonical_url or public_url
            context.update(
                analysis=analyze_page(
                    self.instance,
                    site_hostname=site_hostname,
                ),
                metadata=metadata,
                preview_url=preview_url,
                served_public_url=public_url,
                title_uses_fallback=not bool((self.instance.seo_title or "").strip()),
                description_uses_fallback=not bool(
                    (self.instance.search_description or "").strip(),
                ),
                og_title_uses_fallback=not bool((self.instance.og_title or "").strip()),
                og_description_uses_fallback=not bool(
                    (self.instance.og_description or "").strip(),
                ),
                og_image_uses_fallback=(
                    not self.instance.og_image and bool(self.instance.featured_image)
                ),
            )
            return context

        @property
        def media(self):
            return super().media + forms.Media(
                css=self.Media.css,
                js=self.Media.js,
            )


class PageSeoContextPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "news/admin/page_seo_context_panel.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["draft_preview_url"] = (
                reverse("wagtailadmin_pages:view_draft", args=(self.instance.pk,))
                if self.instance.pk
                else None
            )
            return context


class NewsSeoContextPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "news/admin/news_seo_context_panel.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["draft_preview_url"] = (
                reverse("wagtailadmin_pages:view_draft", args=(self.instance.pk,))
                if self.instance.pk
                else None
            )
            return context
