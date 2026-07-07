from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class NewsSection(models.Model):
    name = models.CharField("Nombre", max_length=80)
    slug = models.SlugField("Slug", max_length=80, unique=True)
    sort_order = models.PositiveSmallIntegerField("Orden", default=100)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Sección editorial"
        verbose_name_plural = "Secciones editoriales"

    def __str__(self) -> str:
        return self.name


class School(models.Model):
    name = models.CharField("Nombre", max_length=160)
    province = models.CharField("Provincia", max_length=80)
    district = models.CharField("Distrito", max_length=80)

    panels = [
        FieldPanel("name"),
        FieldPanel("province"),
        FieldPanel("district"),
    ]

    class Meta:
        ordering = ["name"]
        verbose_name = "Colegio"
        verbose_name_plural = "Colegios"

    def __str__(self) -> str:
        return self.name


class NewsPageTag(TaggedItemBase):
    content_object = ParentalKey(
        "news.NewsPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class NewsPage(Page):
    template = "news/news_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []

    publication_date = models.DateField("Fecha de publicación")
    summary = models.TextField("Resumen", max_length=500)
    body = StreamField(
        [
            (
                "heading",
                blocks.CharBlock(
                    label="Subtítulo",
                    form_classname="title",
                    template="news/blocks/heading.html",
                ),
            ),
            ("paragraph", blocks.RichTextBlock(label="Párrafo")),
        ],
        verbose_name="Contenido",
        blank=False,
        use_json_field=True,
    )
    section = models.ForeignKey(
        NewsSection,
        verbose_name="Sección",
        on_delete=models.PROTECT,
        related_name="news_pages",
    )
    school = models.ForeignKey(
        School,
        verbose_name="Colegio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_pages",
    )
    coverage_province = models.CharField("Provincia de cobertura", max_length=80)
    coverage_district = models.CharField(
        "Distrito de cobertura",
        max_length=80,
        blank=True,
    )
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name="Imagen destacada",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    tags = ClusterTaggableManager("Etiquetas", through=NewsPageTag, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("publication_date"),
        FieldPanel("summary"),
        FieldPanel("body"),
        FieldPanel("section"),
        FieldPanel("school"),
        MultiFieldPanel(
            [
                FieldPanel("coverage_province"),
                FieldPanel("coverage_district"),
            ],
            heading="Cobertura",
        ),
        FieldPanel("featured_image"),
        FieldPanel("tags"),
    ]

    class Meta:
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"
