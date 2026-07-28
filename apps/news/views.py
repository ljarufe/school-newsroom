import json
from urllib.parse import urljoin

from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from wagtail.models import Site

from apps.news.access import FULL_EDITOR_PERMISSION
from apps.news.models import NewsPage, NewsSection
from apps.news.selectors import public_news_pages
from apps.news.seo_metadata import environment_noindex
from apps.news.smart_paste import normalize_paste

SMART_PASTE_MAX_SOURCE_LENGTH = 1_000_000


def robots_txt(request):
    site = Site.find_for_request(request)
    root_url = site.root_url if site is not None else request.build_absolute_uri("/")
    sitemap_url = urljoin(root_url.rstrip("/") + "/", reverse("sitemap").lstrip("/"))
    content = f"User-agent: *\nDisallow:\nSitemap: {sitemap_url}\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def news_list(request):
    section_slug = request.GET.get("seccion", "").strip()
    selected_section = None
    unknown_section_slug = ""
    news_pages = public_news_pages()

    site = Site.find_for_request(request)
    if site is not None:
        news_pages = news_pages.descendant_of(site.root_page)

    if section_slug:
        selected_section = NewsSection.objects.filter(slug=section_slug).first()
        if selected_section is None:
            unknown_section_slug = section_slug
            news_pages = news_pages.none()
        else:
            news_pages = news_pages.filter(section=selected_section)

    return render(
        request,
        "news/news_list.html",
        {
            "news_pages": list(news_pages),
            "selected_section": selected_section,
            "unknown_section_slug": unknown_section_slug,
            "seo_noindex": environment_noindex(),
        },
    )


@require_POST
@permission_required(FULL_EDITOR_PERMISSION, raise_exception=True)
def normalize_smart_paste(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "No se pudo leer el contenido pegado."},
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {"error": "El contenido pegado no tiene un formato válido."},
            status=400,
        )

    html_source = payload.get("html", "")
    plain_text = payload.get("text", "")
    if not isinstance(html_source, str) or not isinstance(plain_text, str):
        return JsonResponse(
            {"error": "El contenido pegado no tiene un formato válido."},
            status=400,
        )
    if len(html_source) + len(plain_text) > SMART_PASTE_MAX_SOURCE_LENGTH:
        return JsonResponse(
            {
                "error": (
                    "La nota pegada es demasiado extensa. Divídela en partes más "
                    "pequeñas e inténtalo de nuevo."
                )
            },
            status=400,
        )

    normalized = normalize_paste(
        html_source=html_source,
        plain_text=plain_text,
    )
    response_payload = normalized.as_dict()
    body_block = NewsPage._meta.get_field("body").stream_block
    for response_block, normalized_block in zip(
        response_payload["blocks"],
        normalized.blocks,
        strict=True,
    ):
        child_block = body_block.child_blocks[normalized_block.block_type]
        response_block["value"] = child_block.get_form_state(
            child_block.to_python(normalized_block.value)
        )

    return JsonResponse(response_payload)
