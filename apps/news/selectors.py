from django.db.models import Prefetch

from .models import NewsPage, NewsPageAttribution, NewsPageSection

PUBLIC_NEWS_ORDERING = ("-publication_date", "-first_published_at")


def public_news_pages():
    return (
        NewsPage.objects.live()
        .public()
        .select_related(
            "school",
            "featured_image",
            "coverage_department",
            "coverage_district__province__department",
        )
        .prefetch_related(
            "tags",
            Prefetch(
                "attributions",
                queryset=(
                    NewsPageAttribution.objects.filter(
                        kind__in=(
                            NewsPageAttribution.Kind.AUTHOR,
                            NewsPageAttribution.Kind.PUBLIC_CREDIT,
                        )
                    )
                    .select_related("author_profile__photo")
                    .order_by("sort_order")
                ),
                to_attr="public_attribution_rows",
            ),
            Prefetch(
                "section_assignments",
                queryset=NewsPageSection.objects.select_related("section__parent"),
            ),
        )
        .order_by(*PUBLIC_NEWS_ORDERING)
    )
