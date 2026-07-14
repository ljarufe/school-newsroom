from urllib.parse import urljoin

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from wagtail.models import Site

from apps.news.models import NewsSection
from apps.news.selectors import public_news_pages
from apps.news.seo_metadata import environment_noindex


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
