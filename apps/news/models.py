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
    ObjectList,
    TabbedInterface,
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
from .panels import SeoAssistantPanel
from .seo_metadata import (
    build_news_article_data,
    build_public_metadata,
    canonical_is_self,
    effective_noindex,
    safe_json_dumps,
    validate_canonical_url,
)

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
    focus_keyphrase = models.CharField(
        "Frase clave objetivo",
        max_length=255,
        blank=True,
        help_text=(
            "Frase exacta principal para el análisis SEO. No bloquea la publicación."
        ),
    )
    og_title = models.CharField(
        "Título para redes sociales",
        max_length=255,
        blank=True,
        help_text="Si queda vacío, se usa el título SEO o el título de la noticia.",
    )
    og_description = models.TextField(
        "Descripción para redes sociales",
        max_length=500,
        blank=True,
        help_text=(
            "Si queda vacía, se usa la descripción meta o el resumen de la noticia."
        ),
    )
    og_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name="Imagen para redes sociales",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Si queda vacía, se usa la imagen destacada.",
    )
    canonical_url = models.URLField(
        "URL canonical",
        max_length=2048,
        blank=True,
        validators=[validate_canonical_url],
        help_text=(
            "Déjala vacía para usar la URL pública de esta noticia. Usa una URL "
            "distinta sólo cuando otra versión deba ser la principal."
        ),
    )
    seo_noindex = models.BooleanField(
        "Excluir de los resultados de búsqueda",
        default=False,
        help_text=(
            "Solicita a los buscadores que no indexen esta noticia. No impide que "
            "la página sea visitada ni bloquea su rastreo."
        ),
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

    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug", heading="Slug de la URL"),
                FieldPanel("seo_title", heading="Título SEO"),
                FieldPanel("search_description", heading="Descripción meta"),
                FieldPanel("focus_keyphrase"),
            ],
            heading="Configuración SEO",
        ),
        MultiFieldPanel(
            [
                FieldPanel("og_title"),
                FieldPanel("og_description"),
                FieldPanel("og_image"),
            ],
            heading="Configuración para redes sociales",
        ),
        MultiFieldPanel(
            [
                FieldPanel("canonical_url"),
                FieldPanel("seo_noindex"),
            ],
            heading="Indexación y canonical",
        ),
        SeoAssistantPanel(),
        MultiFieldPanel(
            [
                HelpPanel(
                    content=(
                        "<p><strong>Esta opción organiza la navegación del sitio y "
                        "no afecta el análisis ni el estado SEO.</strong></p>"
                    ),
                ),
                FieldPanel("show_in_menus"),
            ],
            heading="Navegación y menús",
        ),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Contenido"),
            ObjectList(promote_panels, heading="Asistente SEO"),
            ObjectList(Page.settings_panels, heading="Propiedades"),
        ],
    )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        metadata = build_public_metadata(self, request)
        context["seo_metadata"] = metadata
        context["seo_json_ld"] = safe_json_dumps(
            build_news_article_data(self, metadata),
        )
        return context

    def get_sitemap_urls(self, request=None):
        if effective_noindex(self) or not canonical_is_self(self, request):
            return []
        return super().get_sitemap_urls(request=request)

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
