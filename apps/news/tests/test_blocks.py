import datetime as dt
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from wagtail import blocks
from wagtail.embeds.embeds import get_embed_hash
from wagtail.embeds.models import Embed
from wagtail.images import get_image_model

import apps.news.blocks as news_blocks
from apps.news.blocks import (
    PARAGRAPH_FEATURES,
    ArticleImageBlock,
    SpotifyEmbedBlock,
    YouTubeEmbedBlock,
)
from apps.news.models import NewsPage

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)

YOUTUBE_URL = "https://www.youtube.com/watch?v=fictionalVideo01"
SPOTIFY_URL = "https://open.spotify.com/episode/fictionalEpisode01"


def create_uploaded_image():
    image_model = get_image_model()
    return image_model.objects.create(
        title="Imagen editorial genérica",
        file=SimpleUploadedFile(
            "article-body.gif",
            GIF_BYTES,
            content_type="image/gif",
        ),
    )


def create_cached_embed(url, *, provider_name, html):
    return Embed.objects.create(
        url=url,
        max_width=None,
        hash=get_embed_hash(url, None, None),
        type="rich",
        html=html,
        title="Contenido multimedia ficticio",
        author_name="",
        provider_name=provider_name,
        thumbnail_url="",
        width=None,
        height=None,
        last_updated=timezone.now(),
        cache_until=timezone.now() + dt.timedelta(days=1),
    )


def test_news_body_uses_final_native_block_configuration() -> None:
    stream_block = NewsPage._meta.get_field("body").stream_block
    paragraph = stream_block.child_blocks["paragraph"]

    assert list(stream_block.child_blocks) == [
        "paragraph",
        "article_image",
        "youtube",
        "spotify",
    ]
    assert "heading" not in stream_block.child_blocks
    assert type(paragraph) is blocks.RichTextBlock
    assert paragraph.label == "Párrafo"
    assert (
        paragraph.features
        == PARAGRAPH_FEATURES
        == [
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
    )
    assert "image" not in paragraph.features
    assert "embed" not in paragraph.features
    assert "html" not in paragraph.features


def test_native_paragraph_widget_exposes_only_final_features() -> None:
    paragraph = NewsPage._meta.get_field("body").stream_block.child_blocks["paragraph"]
    widget = paragraph.field.widget
    block_types = [option["type"] for option in widget.options["blockTypes"]]
    entity_types = [option["type"] for option in widget.options["entityTypes"]]

    assert widget.features == PARAGRAPH_FEATURES
    assert block_types == [
        "header-two",
        "header-three",
        "header-four",
        "ordered-list-item",
        "unordered-list-item",
        "blockquote",
    ]
    assert entity_types == ["LINK", "DOCUMENT"]
    assert widget.options["enableHorizontalRule"] is True
    assert "IMAGE" not in entity_types
    assert "EMBED" not in entity_types


def test_paragraph_legacy_compatibility_shim_is_absent() -> None:
    paragraph = NewsPage._meta.get_field("body").stream_block.child_blocks["paragraph"]
    media = str(paragraph.field.widget.media)

    assert "legacy_paragraph_draftail.js" not in media
    assert not Path("static/news/js/legacy_paragraph_draftail.js").exists()
    assert news_blocks.ParagraphBlock is blocks.RichTextBlock
    assert not hasattr(news_blocks, "LegacyPreservingDraftailRichTextArea")
    assert not hasattr(news_blocks, "LegacyPreservingDraftailRichTextAreaAdapter")
    assert not hasattr(news_blocks, "get_legacy_block_types_from_contentstate")
    assert not hasattr(news_blocks, "get_legacy_entity_types_from_contentstate")
    assert not hasattr(paragraph.field.widget, "legacy_runtime_block_options")
    assert not hasattr(paragraph.field.widget, "legacy_runtime_entity_options")


@pytest.mark.django_db
def test_article_image_block_field_order_and_admin_media() -> None:
    block = NewsPage._meta.get_field("body").stream_block.child_blocks["article_image"]
    form_class = NewsPage.get_edit_handler().get_form_class()

    assert isinstance(block, ArticleImageBlock)
    assert list(block.child_blocks) == ["image", "caption", "alt_text", "credit"]
    assert block.child_blocks["image"].label == "Imagen"
    assert block.child_blocks["caption"].label == "Pie de foto"
    assert block.child_blocks["alt_text"].label == "Texto alternativo"
    assert block.child_blocks["credit"].label == "Crédito de imagen"
    assert block.child_blocks["credit"].required is False
    assert "news/js/article_image_block.js" in str(form_class().media)


@pytest.mark.django_db
def test_article_image_full_validation_requires_effective_caption_and_alt(
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    block = ArticleImageBlock()

    with pytest.raises(ValidationError) as exc_info:
        block.clean(
            {
                "image": image,
                "caption": "   ",
                "alt_text": "   ",
                "credit": "",
            },
        )

    assert "caption" in exc_info.value.block_errors
    assert "alt_text" in exc_info.value.block_errors


def test_article_image_full_validation_requires_image() -> None:
    block = ArticleImageBlock()

    with pytest.raises(ValidationError) as exc_info:
        block.clean(
            {
                "image": None,
                "caption": "Pie de foto ficticio.",
                "alt_text": "Descripción alternativa ficticia.",
                "credit": "",
            },
        )

    assert "image" in exc_info.value.block_errors


def test_article_image_deferred_validation_allows_incomplete_draft() -> None:
    stream_block = NewsPage._meta.get_field("body").stream_block
    stream_value = stream_block.to_python(
        [
            {
                "type": "article_image",
                "value": {
                    "image": None,
                    "caption": "",
                    "alt_text": "",
                    "credit": "",
                },
            },
        ],
    )

    assert stream_block.clean_deferred(stream_value)


@pytest.mark.django_db
def test_youtube_block_accepts_supported_youtube_url() -> None:
    block = YouTubeEmbedBlock()
    create_cached_embed(
        YOUTUBE_URL,
        provider_name="YouTube",
        html='<iframe title="YouTube ficticio"></iframe>',
    )

    value = block.value_from_form(YOUTUBE_URL)

    assert block.clean(value).url == YOUTUBE_URL


@pytest.mark.django_db
def test_spotify_block_accepts_supported_spotify_url() -> None:
    block = SpotifyEmbedBlock()
    create_cached_embed(
        SPOTIFY_URL,
        provider_name="Spotify",
        html='<iframe title="Spotify ficticio"></iframe>',
    )

    value = block.value_from_form(SPOTIFY_URL)

    assert block.clean(value).url == SPOTIFY_URL


def test_youtube_block_rejects_wrong_provider_at_block_boundary() -> None:
    block = YouTubeEmbedBlock()
    value = block.value_from_form(SPOTIFY_URL)

    with pytest.raises(ValidationError, match="YouTube"):
        block.clean(value)


def test_youtube_block_rejects_same_provider_url_without_video_id() -> None:
    block = YouTubeEmbedBlock()
    value = block.value_from_form("https://www.youtube.com/watch?v=   ")

    with pytest.raises(ValidationError, match="YouTube"):
        block.clean(value)


def test_spotify_block_rejects_wrong_provider_at_block_boundary() -> None:
    block = SpotifyEmbedBlock()
    value = block.value_from_form(YOUTUBE_URL)

    with pytest.raises(ValidationError, match="Spotify"):
        block.clean(value)


def test_spotify_block_rejects_same_provider_url_without_content_id() -> None:
    block = SpotifyEmbedBlock()
    value = block.value_from_form("https://open.spotify.com/episode/")

    with pytest.raises(ValidationError, match="Spotify"):
        block.clean(value)


def test_provider_embed_unexpected_rendering_exception_is_not_fallback(
    monkeypatch,
) -> None:
    block = YouTubeEmbedBlock()
    value = block.value_from_form(YOUTUBE_URL)

    def fail_unexpectedly(self, value, context=None):
        raise RuntimeError("unexpected rendering failure")

    monkeypatch.setattr(
        "wagtail.embeds.blocks.EmbedBlock.render_basic",
        fail_unexpectedly,
    )

    with pytest.raises(RuntimeError, match="unexpected rendering failure"):
        block.render_basic(value)
