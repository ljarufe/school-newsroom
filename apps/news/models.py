from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import ProtectedError
from django.utils.functional import cached_property
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
    HelpPanel,
    InlinePanel,
    MultiFieldPanel,
    TabbedInterface,
)
from wagtail.fields import StreamField
from wagtail.models import Orderable, Page, Revision

from .access import FULL_EDITOR_PERMISSION, SEO_EDITOR_PERMISSION
from .blocks import (
    PARAGRAPH_FEATURES,
    ArticleImageBlock,
    NewsTableBlock,
    SpotifyEmbedBlock,
    YouTubeEmbedBlock,
)
from .forms import NewsPageAdminForm
from .image_metadata import contextual_metadata_field, effective_text
from .panels import (
    RolePermissionObjectList,
    SeoAssistantPanel,
    TaxonomyPanel,
    WritingModeFieldPanel,
    contextual_image_panels,
)
from .seo_metadata import (
    build_news_article_data,
    build_public_metadata,
    build_public_share_links,
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

CONTENT_AUTHORING_HELP = (
    "Selecciona texto para mostrar la barra contextual de formato. "
    'Usa "/" para insertar o dividir bloques.'
)

PUBLIC_CREDIT_HELP = (
    "Obligatoria para publicar. Puedes dejarla vacía mientras trabajas en un borrador."
)


class NewsSection(models.Model):
    name = models.CharField("Nombre", max_length=80)
    slug = models.SlugField("Slug", max_length=80, unique=True)
    sort_order = models.PositiveSmallIntegerField("Orden", default=100)
    parent = models.ForeignKey(
        "self",
        verbose_name="Sección principal",
        on_delete=models.PROTECT,
        related_name="subsections",
        null=True,
        blank=True,
        limit_choices_to={"parent__isnull": True},
        help_text=(
            "Déjalo vacío para crear una sección principal. Una subsección no "
            "puede contener otras subsecciones."
        ),
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("parent"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "name", "pk"]
        verbose_name = "Sección editorial"
        verbose_name_plural = "Secciones editoriales"

    def __str__(self) -> str:
        if self.parent_id:
            return f"{self.parent.name} › {self.name}"
        return self.name

    @property
    def hierarchical_name(self) -> str:
        return str(self)

    hierarchical_name.fget.short_description = "Clasificación"

    @property
    def classification_type(self) -> str:
        return "Subsección" if self.parent_id else "Sección principal"

    classification_type.fget.short_description = "Tipo"

    def clean(self) -> None:
        super().clean()
        if self.pk and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "Una sección no puede depender de sí misma."}
            )
        if self.parent_id is not None and self.parent.parent_id is not None:
            raise ValidationError(
                {"parent": "Una subsección no puede depender de otra subsección."}
            )

        if not self.pk:
            return

        original_parent_ids = list(
            type(self)
            .objects.filter(pk=self.pk)
            .values_list("parent_id", flat=True)[:1]
        )
        if not original_parent_ids:
            return

        original_parent_id = original_parent_ids[0]
        if original_parent_id is None and self.parent_id is not None:
            raise ValidationError(
                {
                    "parent": (
                        "Una sección principal no puede convertirse en subsección."
                    )
                }
            )
        if original_parent_id is not None and self.parent_id is None:
            raise ValidationError(
                {
                    "parent": (
                        "Una subsección no puede convertirse en sección principal."
                    )
                }
            )

    def is_referenced_by_revision(self) -> bool:
        news_page_content_type = ContentType.objects.get_for_model(NewsPage)
        section_ids = {self.pk}
        from .taxonomy import revision_content_references_section

        return any(
            revision_content_references_section(content, section_ids)
            for content in Revision.objects.filter(
                content_type=news_page_content_type
            ).values_list("content", flat=True)
        )

    def delete(self, *args, **kwargs):
        if self.is_referenced_by_revision():
            raise ProtectedError(
                (
                    "No puedes eliminar esta clasificación porque contiene "
                    "subsecciones o está asociada a noticias."
                ),
                {self},
            )
        return super().delete(*args, **kwargs)


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
            ("table", NewsTableBlock()),
            ("youtube", YouTubeEmbedBlock()),
            ("spotify", SpotifyEmbedBlock()),
        ],
        verbose_name="Contenido",
        blank=False,
        use_json_field=True,
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
        help_text=(
            "Selecciona el archivo principal. Completa debajo su metadata editorial "
            "para esta noticia."
        ),
    )
    featured_image_caption = contextual_metadata_field("caption")
    featured_image_alt_text = contextual_metadata_field("alt_text")
    featured_image_credit = contextual_metadata_field("credit")
    focus_keyphrase = models.CharField(
        "Frase clave principal",
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
            "Si queda vacía, se usa la descripción meta. Si ambas están vacías, "
            "se omite la descripción social."
        ),
    )
    og_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name="Imagen para redes sociales",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=(
            "Si queda vacía, se usa la imagen destacada y su texto alternativo "
            "contextual."
        ),
    )
    og_image_caption = contextual_metadata_field("caption")
    og_image_alt_text = contextual_metadata_field("alt_text")
    og_image_credit = contextual_metadata_field("credit")
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
        MultiFieldPanel(
            contextual_image_panels("featured_image", "featured_image"),
            heading="Imagen destacada",
        ),
        WritingModeFieldPanel("body", help_text=CONTENT_AUTHORING_HELP),
        TaxonomyPanel("taxonomy_sections"),
        MultiFieldPanel(
            [
                FieldPanel("coverage_province"),
                FieldPanel("coverage_district"),
            ],
            heading="Cobertura",
        ),
        FieldPanel("publication_date"),
        FieldPanel("tags"),
        FieldPanel("school"),
        InlinePanel("internal_contributors", label="Colaboradores internos"),
        InlinePanel(
            "public_credits",
            label="Firma pública",
            help_text=PUBLIC_CREDIT_HELP,
        ),
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
                InlinePanel(
                    "related_keyphrases",
                    label="Frase clave relacionada",
                    heading="Frases clave relacionadas",
                    help_text=(
                        "Añade hasta cuatro frases relacionadas que también "
                        "describan el tema. Se analizan con menos exigencia que la "
                        "frase principal."
                    ),
                    max_num=4,
                ),
            ],
            heading="Configuración SEO",
        ),
        MultiFieldPanel(
            [
                FieldPanel("og_title"),
                FieldPanel("og_description"),
                MultiFieldPanel(
                    contextual_image_panels("og_image", "og_image"),
                    heading="Imagen social y metadata editorial",
                ),
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
                FieldPanel("show_in_menus", permission=FULL_EDITOR_PERMISSION),
            ],
            heading="Navegación y menús",
            permission=FULL_EDITOR_PERMISSION,
        ),
    ]

    edit_handler = TabbedInterface(
        [
            RolePermissionObjectList(
                content_panels,
                heading="Edición de la noticia",
                permission=FULL_EDITOR_PERMISSION,
            ),
            RolePermissionObjectList(
                promote_panels,
                heading="Asistente SEO",
                permission=SEO_EDITOR_PERMISSION,
            ),
            RolePermissionObjectList(
                Page.settings_panels,
                heading="Propiedades",
                permission=FULL_EDITOR_PERMISSION,
            ),
        ],
    )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        metadata = build_public_metadata(self, request)
        context["seo_metadata"] = metadata
        context["seo_json_ld"] = safe_json_dumps(
            build_news_article_data(self, metadata),
        )
        if self.live and not getattr(request, "is_preview", False):
            context["public_share"] = build_public_share_links(metadata)
        return context

    @cached_property
    def taxonomy(self):
        from .taxonomy import NewsTaxonomy

        return NewsTaxonomy.from_page(self)

    def get_sitemap_urls(self, request=None):
        if effective_noindex(self) or not canonical_is_self(self, request):
            return []
        return super().get_sitemap_urls(request=request)

    @property
    def effective_featured_image_caption(self) -> str:
        return effective_text(self.featured_image_caption)

    @property
    def effective_featured_image_alt_text(self) -> str:
        return effective_text(self.featured_image_alt_text)

    @property
    def effective_featured_image_credit(self) -> str:
        return effective_text(self.featured_image_credit)

    class Meta:
        permissions = [
            (
                "access_full_editorial_surfaces",
                "Puede acceder a todas las superficies editoriales del MVP",
            ),
            (
                "access_seo_editorial_surface",
                "Puede acceder a la superficie editorial SEO del MVP",
            ),
        ]
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"


class NewsPageRelatedKeyphrase(Orderable):
    page = ParentalKey(
        NewsPage,
        related_name="related_keyphrases",
        on_delete=models.CASCADE,
    )
    phrase = models.CharField("Frase relacionada", max_length=255)

    panels = [FieldPanel("phrase")]

    class Meta(Orderable.Meta):
        verbose_name = "Frase clave relacionada"
        verbose_name_plural = "Frases clave relacionadas"

    def __str__(self) -> str:
        return self.phrase


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


class NewsPageSection(models.Model):
    page = ParentalKey(
        NewsPage,
        related_name="section_assignments",
        on_delete=models.CASCADE,
    )
    section = models.ForeignKey(
        NewsSection,
        verbose_name="Sección o subsección",
        on_delete=models.PROTECT,
        related_name="news_page_assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("page", "section"),
                name="unique_news_page_section",
            )
        ]
        verbose_name = "Clasificación de noticia"
        verbose_name_plural = "Clasificaciones de noticia"

    def __str__(self) -> str:
        return str(self.section)


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
