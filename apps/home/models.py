from wagtail.models import Page


class HomePage(Page):
    template = "home/home_page.html"
    max_count = 1
    subpage_types = ["news.NewsPage"]

    class Meta:
        verbose_name = "Página de inicio"
        verbose_name_plural = "Páginas de inicio"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        from apps.news.models import NewsPage

        context["latest_news"] = (
            NewsPage.objects.live()
            .public()
            .descendant_of(self)
            .select_related("section", "school", "featured_image")
            .order_by("-publication_date", "-first_published_at")[:12]
        )
        return context
