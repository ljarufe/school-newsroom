"""Cohesive implementations registered by the Wagtail discovery module."""

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.urls import path
from wagtail.models import Page, Revision

from .models import NewsPage, NewsPageSection, NewsSection
from .taxonomy import revision_content_references_section
from .views import normalize_smart_paste


def news_section_deletion_is_protected(sections) -> bool:
    section_ids = {section.pk for section in sections}
    if NewsSection.objects.filter(parent_id__in=section_ids).exists():
        return True
    if NewsPageSection.objects.filter(section_id__in=section_ids).exists():
        return True

    news_page_content_type = ContentType.objects.get_for_model(NewsPage)
    return any(
        revision_content_references_section(content, section_ids)
        for content in Revision.objects.filter(
            content_type=news_page_content_type
        ).values_list("content", flat=True)
    )


def news_section_deletion_protection_response(
    request,
    sections,
    *,
    redirect_name,
):
    if not news_section_deletion_is_protected(sections):
        return None

    messages.error(
        request,
        (
            "No puedes eliminar esta clasificación porque contiene subsecciones "
            "o está asociada a noticias."
        ),
    )
    return redirect(redirect_name)


def protect_news_section_deletion(request, snippets):
    sections = [snippet for snippet in snippets if isinstance(snippet, NewsSection)]
    if not sections:
        return None

    if any(section.parent_id is not None for section in sections):
        messages.error(
            request,
            "La clasificación solicitada no está disponible en Secciones.",
        )
        return redirect("wagtailsnippets_news_newssection:list")

    return news_section_deletion_protection_response(
        request,
        sections,
        redirect_name="wagtailsnippets_news_newssection:list",
    )


def register_news_admin_urls():
    return [
        path(
            "news/smart-paste/normalize/",
            normalize_smart_paste,
            name="news_smart_paste_normalize",
        ),
    ]


def redirect_after_workflow_action_when_edit_access_ends(request, page):
    """Keep completed moderation actions away from a now-forbidden edit view."""
    if request.method != "POST" or "action-workflow-action" not in request.POST:
        return None

    refreshed_page = Page.objects.get(pk=page.pk).specific
    if refreshed_page.permissions_for_user(request.user).can_edit():
        return None
    return redirect("wagtailadmin_home")
