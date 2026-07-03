from wagtail.models import Page


class HomePage(Page):
    template = "home/home_page.html"
    max_count = 1
