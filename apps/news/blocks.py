from urllib.parse import parse_qs, urlsplit

from django import forms
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.utils.html import format_html
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock

from .image_metadata import (
    ALT_TEXT_HELP_TEXT,
    ALT_TEXT_LABEL,
    CAPTION_LABEL,
    CREDIT_LABEL,
)

PARAGRAPH_FEATURES = [
    "bold",
    "italic",
    "link",
    "h2",
    "h3",
    "h4",
    "ol",
    "ul",
    "blockquote",
    "hr",
    "document-link",
]

# Migration 0004 serializes this import path. Keep it as a native-class alias so
# historical migration state remains loadable without retaining the old shim.
ParagraphBlock = blocks.RichTextBlock


class ArticleImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(label="Imagen")
    caption = blocks.CharBlock(label=CAPTION_LABEL)
    alt_text = blocks.CharBlock(
        label=ALT_TEXT_LABEL,
        help_text=ALT_TEXT_HELP_TEXT,
    )
    credit = blocks.CharBlock(label=CREDIT_LABEL, required=False)

    class Meta:
        icon = "image"
        label = "Imagen"
        template = "news/blocks/article_image.html"


class ArticleImageBlockAdapter(StructBlockAdapter):
    js_constructor = "schoolNewsroom.blocks.ArticleImageBlock"

    @cached_property
    def media(self):
        return super().media + forms.Media(
            js=[
                "news/js/caption_alt_sync.js",
                "news/js/article_image_block.js",
            ],
        )


register(ArticleImageBlockAdapter(), ArticleImageBlock)


class ProviderEmbedBlock(EmbedBlock):
    allowed_provider = ""
    fallback_label = ""
    invalid_provider_message = "La URL no pertenece al proveedor permitido."

    def clean(self, value):
        if value:
            url = value.url if hasattr(value, "url") else str(value)
            try:
                is_allowed = self.is_allowed_url(url)
            except ValueError as exc:
                raise ValidationError(self.invalid_provider_message) from exc
            if not is_allowed:
                raise ValidationError(self.invalid_provider_message)
        return super().clean(value)

    def render_basic(self, value, context=None):
        if not value:
            return ""

        html = super().render_basic(value, context=context)

        if html:
            return html

        url = value.url if hasattr(value, "url") else str(value)
        return format_html(
            '<p><a href="{}" rel="noopener noreferrer">{}</a></p>',
            url,
            self.fallback_label,
        )

    def is_allowed_url(self, url):
        raise NotImplementedError

    class Meta:
        icon = "media"


class YouTubeEmbedBlock(ProviderEmbedBlock):
    fallback_label = "Ver contenido en YouTube"
    invalid_provider_message = "Ingresa una URL válida de YouTube."

    def is_allowed_url(self, url):
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/")

        if hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if path == "/watch":
                return bool(parse_qs(parsed.query).get("v", [""])[0].strip())
            if path.startswith("/embed/"):
                return bool(path.removeprefix("/embed/").strip("/"))
            if path.startswith("/shorts/"):
                return bool(path.removeprefix("/shorts/").strip("/"))
            return False

        if hostname == "youtu.be":
            return bool(path.strip("/"))

        return False

    class Meta:
        label = "Video de YouTube"
        icon = "media"


class SpotifyEmbedBlock(ProviderEmbedBlock):
    fallback_label = "Escuchar en Spotify"
    invalid_provider_message = "Ingresa una URL válida de Spotify."
    allowed_content_paths = {"album", "episode", "playlist", "show", "track"}

    def is_allowed_url(self, url):
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower()
        path_parts = [part for part in parsed.path.split("/") if part]

        return (
            hostname == "open.spotify.com"
            and len(path_parts) >= 2
            and path_parts[0] in self.allowed_content_paths
            and bool(path_parts[1].strip())
        )

    class Meta:
        label = "Audio o pódcast de Spotify"
        icon = "media"
