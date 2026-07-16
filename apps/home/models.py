from django.db import models
from wagtail.admin.panels import (
    FieldPanel,
    HelpPanel,
    MultiFieldPanel,
    TabbedInterface,
)
from wagtail.fields import RichTextField
from wagtail.models import Page

from apps.news.access import FULL_EDITOR_PERMISSION, SEO_EDITOR_PERMISSION
from apps.news.panels import PageSeoContextPanel, RolePermissionObjectList
from apps.news.seo_metadata import environment_noindex

from .forms import HomePageAdminForm, InstitutionalPageAdminForm


def mvp_page_edit_handler(content_panels):
    return TabbedInterface(
        [
            RolePermissionObjectList(
                content_panels,
                heading="Contenido",
                permission=FULL_EDITOR_PERMISSION,
            ),
            RolePermissionObjectList(
                [
                    PageSeoContextPanel(),
                    MultiFieldPanel(
                        [
                            FieldPanel("slug", heading="Slug de la URL"),
                            FieldPanel("seo_title", heading="Título SEO"),
                            FieldPanel(
                                "search_description",
                                heading="Descripción meta",
                            ),
                        ],
                        heading="Configuración SEO",
                    ),
                    HelpPanel(
                        content=(
                            "<p>Esta página usa los campos SEO nativos. La noticia "
                            "dispone además del checklist completo del Asistente "
                            "SEO.</p>"
                        ),
                    ),
                    MultiFieldPanel(
                        [
                            HelpPanel(
                                content=(
                                    "<p><strong>Esta opción organiza la navegación "
                                    "del sitio y no es un campo SEO.</strong></p>"
                                ),
                            ),
                            FieldPanel(
                                "show_in_menus",
                                permission=FULL_EDITOR_PERMISSION,
                            ),
                        ],
                        heading="Navegación y menús",
                        permission=FULL_EDITOR_PERMISSION,
                    ),
                ],
                heading="Asistente SEO",
                permission=SEO_EDITOR_PERMISSION,
            ),
            RolePermissionObjectList(
                Page.settings_panels,
                heading="Propiedades",
                permission=FULL_EDITOR_PERMISSION,
            ),
        ],
    )


class HomePage(Page):
    template = "home/home_page.html"
    max_count = 1
    subpage_types = ["news.NewsPage", "home.InstitutionalPage"]
    base_form_class = HomePageAdminForm
    edit_handler = mvp_page_edit_handler(Page.content_panels)

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
    base_form_class = InstitutionalPageAdminForm

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
    edit_handler = mvp_page_edit_handler(content_panels)

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
