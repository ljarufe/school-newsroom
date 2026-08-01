from django.db.models import Prefetch

from .models import NewsPage, NewsPagePublicCredit, NewsPageSection

PUBLIC_NEWS_ORDERING = ("-publication_date", "-first_published_at")


def public_news_pages():
    return (
        NewsPage.objects.live()
        .public()
        .select_related("school", "featured_image")
        .prefetch_related(
            Prefetch(
                "public_credits",
                queryset=NewsPagePublicCredit.objects.order_by("sort_order"),
            ),
            Prefetch(
                "section_assignments",
                queryset=NewsPageSection.objects.select_related("section__parent"),
            ),
        )
        .order_by(*PUBLIC_NEWS_ORDERING)
    )
