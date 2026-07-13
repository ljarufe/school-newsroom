import json
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from wagtail.models import Site


@dataclass(frozen=True)
class PublicMetadata:
    title: str
    description: str
    canonical_url: str
    robots: str
    og_title: str
    og_description: str
    og_image_url: str
    og_type: str
    site_name: str
    twitter_card: str


def validate_canonical_url(value: str) -> None:
    if not value:
        return
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("La URL canonical debe usar HTTP o HTTPS.")
    if parsed.fragment:
        raise ValidationError("La URL canonical no debe incluir un fragmento.")


def environment_noindex() -> bool:
    return settings.SEO_DEFAULT_NOINDEX


def effective_noindex(page=None) -> bool:
    return environment_noindex() or bool(getattr(page, "seo_noindex", False))


def served_public_url(page, request=None) -> str:
    if not getattr(page, "pk", None):
        return ""
    return page.get_full_url(request=request) or ""


def canonical_url(page, request=None) -> str:
    configured = (getattr(page, "canonical_url", "") or "").strip()
    return configured or served_public_url(page, request)


def canonical_is_self(page, request=None) -> bool:
    served_url = served_public_url(page, request)
    return bool(served_url) and canonical_url(page, request) == served_url


def _site_for_request(page, request=None):
    site = Site.find_for_request(request) if request is not None else None
    if site is not None:
        return site
    if getattr(page, "pk", None):
        return page.get_site()
    return Site.objects.filter(is_default_site=True).first()


def _absolute_image_url(image, request=None) -> str:
    if not image:
        return ""
    rendition = image.get_rendition("fill-1200x630")
    if request is not None:
        return request.build_absolute_uri(rendition.url)
    return rendition.full_url


def build_public_metadata(page, request=None) -> PublicMetadata:
    title = (page.seo_title or "").strip() or (page.title or "").strip()
    description = (page.search_description or "").strip() or (
        page.summary or ""
    ).strip()
    og_title = (page.og_title or "").strip() or title
    og_description = (page.og_description or "").strip() or description
    image = page.og_image or page.featured_image
    site = _site_for_request(page, request)
    site_name = ((site.site_name if site else "") or settings.WAGTAIL_SITE_NAME).strip()
    image_url = _absolute_image_url(image, request)
    return PublicMetadata(
        title=title,
        description=description,
        canonical_url=canonical_url(page, request),
        robots="noindex, follow" if effective_noindex(page) else "index, follow",
        og_title=og_title,
        og_description=og_description,
        og_image_url=image_url,
        og_type="article",
        site_name=site_name,
        twitter_card="summary_large_image" if image_url else "summary",
    )


def build_news_article_data(page, metadata: PublicMetadata) -> dict:
    data: dict = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": page.title,
        "mainEntityOfPage": metadata.canonical_url,
        "publisher": {
            "@type": "Organization",
            "name": metadata.site_name,
        },
    }
    if page.publication_date:
        data["datePublished"] = page.publication_date.isoformat()
    if metadata.description:
        data["description"] = metadata.description
    if page.last_published_at:
        data["dateModified"] = page.last_published_at.isoformat()
    if metadata.og_image_url:
        data["image"] = metadata.og_image_url
    authors = [
        {"name": name.strip()}
        for name in page.public_credits.values_list("display_name", flat=True)
        if name.strip()
    ]
    if authors:
        data["author"] = authors
    return data


def safe_json_dumps(value: dict) -> str:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003C")
        .replace(">", "\\u003E")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
