from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
    HelpPanel,
    InlinePanel,
    MultiFieldPanel,
)
from wagtail.fields import StreamField
from wagtail.models import Orderable, Page

from .blocks import (
    PARAGRAPH_FEATURES,
    ArticleImageBlock,
    SpotifyEmbedBlock,
    YouTubeEmbedBlock,
)
from .forms import NewsPageAdminForm

MINOR_PRIVACY_NOTICE = """
<p>
  El Reglamento de la Ley N.º 29733 contempla criterios diferenciados para
  menores de 14 años y adolescentes de 14 a 17 años en servicios digitales.
  Los artículos 22 a 25 describen supuestos de consentimiento de quien ejerce
  patria potestad o tutela para menores de 14 años, y supuestos de
  consentimiento propio de adolescentes según su capacidad y con información
  expresada en lenguaje comprensible.
</p>
<p>
  En Noticias, la exposición pública de cualquier menor identificable requiere
  que el editor confirme que verificó las autorizaciones requeridas por la
  política del proyecto. Este aviso no sustituye una revisión legal profesional.
  Fuente oficial:
  <a href="https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=23"
     target="_blank" rel="noopener noreferrer">Reglamento de la Ley N.º 29733</a>.
</p>
"""

CONTENT_AUTHORING_HELP = """
<h2>Cómo editar el contenido</h2>
<p>
  Selecciona texto para mostrar la barra de formato y usa el pin para mantenerla
  visible. Pulsa "/" para insertar o dividir bloques. El editor admite atajos de
  escritura tipo Markdown para los formatos disponibles.
</p>
"""

PUBLIC_CREDIT_HELP = (
    "Obligatoria para publicar. Puedes dejarla vacía mientras trabajas en un borrador."
)


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


class ContributorGroup(models.Model):
    name = models.CharField(
        "Nombre",
        max_length=160,
        help_text="Nombre interno del grupo, taller o equipo de colaboradores.",
    )
    school = models.ForeignKey(
        School,
        verbose_name="Colegio",
        on_delete=models.PROTECT,
        related_name="contributor_groups",
        help_text="Colegio al que pertenece este grupo interno.",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("school"),
    ]

    class Meta:
        ordering = ["school__name", "name"]
        verbose_name = "Grupo de colaboradores"
        verbose_name_plural = "Grupos de colaboradores"

    def __str__(self) -> str:
        return f"{self.name} ({self.school})"


class MinorContributor(models.Model):
    class AgeBand(models.TextChoices):
        UNDER_14 = "under_14", "Menor de 14 años"
        FROM_14_TO_17 = "14_to_17", "De 14 a 17 años"

    full_name = models.CharField(
        "Nombre interno",
        max_length=160,
        help_text=(
            "Nombre completo para trazabilidad editorial interna; no se publica "
            "automáticamente."
        ),
    )
    group = models.ForeignKey(
        ContributorGroup,
        verbose_name="Grupo",
        on_delete=models.PROTECT,
        related_name="minor_contributors",
        help_text="Grupo interno del colaborador menor.",
    )
    age_band = models.CharField(
        "Franja de edad",
        max_length=16,
        choices=AgeBand.choices,
        help_text="No registrar fecha de nacimiento ni edad exacta.",
    )

    panels = [
        FieldPanel("full_name"),
        FieldPanel("group"),
        FieldPanel("age_band"),
    ]

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Colaborador menor"
        verbose_name_plural = "Colaboradores menores"

    def __str__(self) -> str:
        return self.full_name

    @property
    def school(self) -> School:
        return self.group.school


class NewsPageTag(TaggedItemBase):
    content_object = ParentalKey(
        "news.NewsPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class NewsPage(Page):
    template = "news/news_page.html"
    base_form_class = NewsPageAdminForm
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []

    publication_date = models.DateField("Fecha de publicación")
    summary = models.TextField("Resumen", max_length=500)
    body = StreamField(
        [
            (
                "paragraph",
                blocks.RichTextBlock(
                    label="Párrafo",
                    features=PARAGRAPH_FEATURES,
                ),
            ),
            ("article_image", ArticleImageBlock()),
            ("youtube", YouTubeEmbedBlock()),
            ("spotify", SpotifyEmbedBlock()),
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
    contains_identifiable_minors = models.BooleanField(
        "Contiene menores identificables",
        default=False,
        help_text=(
            "Marca esta opción si la noticia puede identificar a menores por "
            "nombre o firma pública, imagen reconocible, voz, video u otra "
            "información que haga identificable al menor."
        ),
    )
    minor_publication_authorizations_verified = models.BooleanField(
        (
            "Confirmo que se verificaron las autorizaciones requeridas para "
            "exponer públicamente a los menores identificables de esta noticia"
        ),
        default=False,
        help_text=(
            "Declaración operacional del editor. Los documentos de autorización "
            "no se almacenan en el CMS en esta versión."
        ),
    )
    sensitive_content = models.BooleanField(
        "Contenido sensible",
        default=False,
        help_text=(
            "Señal editorial para contenido social, denuncia u otro tratamiento "
            "delicado que merece especial criterio y una firma pública protectora "
            "cuando corresponda."
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("publication_date"),
        FieldPanel("summary"),
        HelpPanel(content=CONTENT_AUTHORING_HELP),
        FieldPanel("body"),
        InlinePanel(
            "public_credits",
            label="Firma pública",
            help_text=PUBLIC_CREDIT_HELP,
        ),
        InlinePanel("internal_contributors", label="Colaboradores internos"),
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
        MultiFieldPanel(
            [
                HelpPanel(content=MINOR_PRIVACY_NOTICE),
                FieldPanel("contains_identifiable_minors"),
                FieldPanel("minor_publication_authorizations_verified"),
                FieldPanel("sensitive_content"),
            ],
            heading="Privacidad de menores",
        ),
    ]

    class Meta:
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"


class NewsPageContributor(Orderable):
    page = ParentalKey(
        NewsPage,
        related_name="internal_contributors",
        on_delete=models.CASCADE,
    )
    contributor = models.ForeignKey(
        MinorContributor,
        verbose_name="Colaborador menor",
        on_delete=models.PROTECT,
        related_name="news_page_contributions",
    )

    panels = [
        FieldPanel("contributor"),
    ]

    class Meta(Orderable.Meta):
        unique_together = [("page", "contributor")]
        verbose_name = "Colaborador interno de noticia"
        verbose_name_plural = "Colaboradores internos de noticia"

    def __str__(self) -> str:
        return str(self.contributor)


class NewsPagePublicCredit(Orderable):
    page = ParentalKey(
        NewsPage,
        related_name="public_credits",
        on_delete=models.CASCADE,
    )
    display_name = models.CharField(
        "Firma pública",
        max_length=255,
        help_text=(
            "Texto público elegido por el editor. No se deriva automáticamente "
            "de colaboradores internos, colegios ni usuarios."
        ),
    )

    panels = [
        FieldPanel("display_name"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Firma pública"
        verbose_name_plural = "Firmas públicas"

    def __str__(self) -> str:
        return self.display_name
