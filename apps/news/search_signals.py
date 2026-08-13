"""Keep public tag text synchronized with Wagtail's native search index."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from modelsearch import index

from .models import NewsPage, NewsPageTag


@receiver(post_save, sender=NewsPageTag)
@receiver(post_delete, sender=NewsPageTag)
def reindex_page_after_tag_change(sender, instance, **kwargs) -> None:
    """Taggit changes do not save the parent Page, so reindex it explicitly."""
    page = NewsPage.objects.filter(pk=instance.content_object_id).first()
    if page is not None:
        index.insert_or_update_object(page)
