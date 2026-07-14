from django.db.models import Prefetch

from .models import NewsPage, NewsPagePublicCredit

PUBLIC_NEWS_ORDERING = ("-publication_date", "-first_published_at")


def public_news_pages():
    return (
        NewsPage.objects.live()
        .public()
        .select_related("section", "school", "featured_image")
        .prefetch_related(
            Prefetch(
                "public_credits",
                queryset=NewsPagePublicCredit.objects.order_by("sort_order"),
            ),
        )
        .order_by(*PUBLIC_NEWS_ORDERING)
    )
