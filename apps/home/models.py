from django.db.models import Prefetch
from wagtail.models import Page

from apps.news.seo_metadata import environment_noindex


class HomePage(Page):
    template = "home/home_page.html"
    max_count = 1
    subpage_types = ["news.NewsPage"]

    class Meta:
        verbose_name = "Página de inicio"
        verbose_name_plural = "Páginas de inicio"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        from apps.news.models import NewsPage, NewsPagePublicCredit

        context["latest_news"] = (
            NewsPage.objects.live()
            .public()
            .descendant_of(self)
            .select_related("section", "school", "featured_image")
            .prefetch_related(
                Prefetch(
                    "public_credits",
                    queryset=NewsPagePublicCredit.objects.order_by("sort_order"),
                ),
            )
            .order_by("-publication_date", "-first_published_at")[:12]
        )
        context["seo_noindex"] = environment_noindex()
        return context

    def get_sitemap_urls(self, request=None):
        if environment_noindex():
            return []
        return super().get_sitemap_urls(request=request)
