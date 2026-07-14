from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from apps.news.seo_metadata import environment_noindex


class HomePage(Page):
    template = "home/home_page.html"
    max_count = 1
    subpage_types = ["news.NewsPage", "home.InstitutionalPage"]

    class Meta:
        verbose_name = "Página de inicio"
        verbose_name_plural = "Páginas de inicio"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        from apps.news.selectors import public_news_pages

        latest_news = list(public_news_pages().descendant_of(self)[:12])
        context["latest_news"] = latest_news
        context["featured_news"] = latest_news[0] if latest_news else None
        context["secondary_news"] = latest_news[1:]
        context["seo_noindex"] = environment_noindex()
        return context

    def get_sitemap_urls(self, request=None):
        if environment_noindex():
            return []
        return super().get_sitemap_urls(request=request)


class InstitutionalPage(Page):
    template = "home/institutional_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []

    introduction = models.TextField(
        "Introducción",
        max_length=400,
        help_text="Resume el propósito de esta página en uno o dos párrafos breves.",
    )
    body = RichTextField(
        "Contenido",
        features=["bold", "italic", "link", "h2", "h3", "ul", "ol", "blockquote"],
        help_text=(
            "Usa subtítulos, enlaces, listas y citas para organizar contenido "
            "institucional sencillo."
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("introduction"),
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "Página institucional"
        verbose_name_plural = "Páginas institucionales"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["seo_noindex"] = environment_noindex()
        return context

    def get_sitemap_urls(self, request=None):
        if environment_noindex():
            return []
        return super().get_sitemap_urls(request=request)
