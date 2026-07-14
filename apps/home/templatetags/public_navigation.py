from django import template
from wagtail.models import Site

from apps.home.models import HomePage, InstitutionalPage
from apps.news.models import NewsSection

register = template.Library()


@register.inclusion_tag("includes/public_navigation.html", takes_context=True)
def public_navigation(context):
    request = context.get("request")
    site = Site.find_for_request(request) if request is not None else None
    home_page = None
    institutional_pages = InstitutionalPage.objects.none()

    if site is not None:
        candidate = site.root_page.specific
        if isinstance(candidate, HomePage):
            home_page = candidate
            institutional_pages = (
                InstitutionalPage.objects.live()
                .public()
                .child_of(home_page)
                .filter(show_in_menus=True)
                .order_by("path")
            )

    return {
        "request": request,
        "home_page": home_page,
        "sections": NewsSection.objects.all(),
        "institutional_pages": institutional_pages,
    }
