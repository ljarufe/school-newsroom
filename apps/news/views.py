from urllib.parse import urljoin

from django.http import HttpResponse
from django.urls import reverse
from wagtail.models import Site


def robots_txt(request):
    site = Site.find_for_request(request)
    root_url = site.root_url if site is not None else request.build_absolute_uri("/")
    sitemap_url = urljoin(root_url.rstrip("/") + "/", reverse("sitemap").lstrip("/"))
    content = f"User-agent: *\nDisallow:\nSitemap: {sitemap_url}\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")
