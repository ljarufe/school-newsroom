from urllib.parse import urlencode, urljoin

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from wagtail.models import Site

from apps.news.archive import NewsArchiveCriteria, NewsArchiveQueryService
from apps.news.seo_metadata import environment_noindex
from apps.news.smart_paste_views import normalize_smart_paste

__all__ = ("news_list", "normalize_smart_paste", "robots_txt")


def robots_txt(request):
    site = Site.find_for_request(request)
    root_url = site.root_url if site is not None else request.build_absolute_uri("/")
    sitemap_url = urljoin(root_url.rstrip("/") + "/", reverse("sitemap").lstrip("/"))
    content = f"User-agent: *\nDisallow:\nSitemap: {sitemap_url}\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def news_list(request):
    criteria = NewsArchiveCriteria.from_querydict(request.GET)
    service = NewsArchiveQueryService(criteria, request)
    archive = service.execute()
    paginator = Paginator(archive.results, 10)
    page_obj = paginator.get_page(criteria.page_number)
    next_order = "desc" if criteria.order == "asc" else "asc"
    order_criteria = criteria.__class__(
        search=criteria.search,
        section_slug=criteria.section_slug,
        subsection_slug=criteria.subsection_slug,
        tag_slug=criteria.tag_slug,
        order=next_order,
    )
    root_sections = [section for section in service.sections if not section.parent_id]
    subsections_by_parent = {section.pk: [] for section in root_sections}
    for section in service.sections:
        if section.parent_id:
            subsections_by_parent[section.parent_id].append(section)

    return render(
        request,
        "news/news_list.html",
        {
            "news_pages": page_obj.object_list,
            "page_obj": page_obj,
            "criteria": criteria,
            "archive": archive,
            "section_hierarchy": [
                (section, subsections_by_parent[section.pk])
                for section in root_sections
            ],
            "selected_section": archive.selected_section,
            "pagination_query": urlencode(criteria.query_parameters()),
            "order_toggle_query": urlencode(order_criteria.query_parameters()),
            "seo_noindex": environment_noindex() or criteria.has_effective_search,
        },
    )
