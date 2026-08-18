from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import ProtectedError
from django.utils.functional import cached_property
from django.utils.text import slugify
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
from wagtail.search import index

from apps.geography.widgets import DependentDistrictWidget

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

ATTRIBUTION_HELP = (
    "Añade autores públicos, firmas públicas o colaboradores internos. "
    "Puedes dejar la lista incompleta mientras trabajas en un borrador."
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
    department = models.ForeignKey(
        "geography.Department",
        verbose_name="Departamento",
        on_delete=models.PROTECT,
        related_name="schools",
    )
    district = models.ForeignKey(
        "geography.District",
        verbose_name="Distrito",
        on_delete=models.PROTECT,
        related_name="schools",
        null=True,
        blank=True,
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("department"),
        FieldPanel(
            "district",
            widget=DependentDistrictWidget(department_field="department"),
        ),
    ]

    class Meta:
        ordering = ["name"]
        verbose_name = "Colegio"
        verbose_name_plural = "Colegios"

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if (
            self.district_id
            and self.department_id
            and self.district.province.department_id != self.department_id
        ):
            raise ValidationError(
                {"district": "El distrito debe pertenecer al departamento elegido."}
            )


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


class AuthorProfile(models.Model):
    """A deliberately editorial public identity, never an account projection."""

    display_name = models.CharField("Nombre público", max_length=160)
    slug = models.SlugField("Slug", max_length=160, unique=True)
    photo = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name="Foto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="author_profiles",
    )
    bio = models.TextField("Biografía", blank=True)
    email = models.EmailField("Correo público", blank=True)
    position = models.CharField("Cargo", max_length=160, blank=True)
    work_url = models.URLField("URL de trabajo", blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuario interno relacionado",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="author_profile",
    )
    minor_contributor = models.OneToOneField(
        MinorContributor,
        verbose_name="Colaborador menor relacionado",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="author_profile",
    )
    is_active = models.BooleanField(
        "Activo para nuevas autorías",
        default=True,
        help_text=(
            "Desactiva el perfil para conservar su historial sin ofrecerlo en "
            "nuevas autorías."
        ),
    )

    panels = [
        FieldPanel("display_name"),
        FieldPanel("slug"),
        FieldPanel("photo"),
        FieldPanel("bio"),
        FieldPanel("email"),
        FieldPanel("position"),
        FieldPanel("work_url"),
        FieldPanel("user"),
        FieldPanel("minor_contributor"),
        FieldPanel("is_active"),
    ]

    class Meta:
        ordering = ["display_name", "pk"]
        verbose_name = "Perfil público de autor"
        verbose_name_plural = "Perfiles públicos de autor"
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~(
                        models.Q(user__isnull=False)
                        & models.Q(minor_contributor__isnull=False)
                    )
                ),
                name="author_profile_internal_identity_is_exclusive",
            ),
            models.CheckConstraint(
                condition=models.Q(minor_contributor__isnull=True) | models.Q(email=""),
                name="author_profile_minor_email_is_empty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            max_length = self._meta.get_field("slug").max_length
            base_slug = (slugify(self.display_name) or "autor")[:max_length]
            candidate = base_slug
            suffix = 2
            while (
                type(self)
                ._default_manager.exclude(pk=self.pk)
                .filter(slug=candidate)
                .exists()
            ):
                suffix_text = f"-{suffix}"
                candidate = f"{base_slug[: max_length - len(suffix_text)]}{suffix_text}"
                suffix += 1
            self.slug = candidate
        return super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.user_id and self.minor_contributor_id:
            raise ValidationError(
                "Un perfil público solo puede relacionarse con una identidad interna."
            )
        if self.minor_contributor_id and self.email.strip():
            raise ValidationError(
                {"email": "Un perfil público de menor no puede incluir correo."}
            )


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

    search_fields = Page.search_fields + [
        # Four distinct boosts map to PostgreSQL's four weights.  The public
        # archive contract requires title > tag > body.
        index.SearchField("title", boost=16),
        index.RelatedFields("tags", [index.SearchField("name", boost=8)]),
        index.SearchField("body", boost=4),
        index.FilterField("publication_date"),
        index.FilterField("first_published_at"),
    ]

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
    coverage_department = models.ForeignKey(
        "geography.Department",
        verbose_name="Departamento",
        on_delete=models.PROTECT,
        related_name="covered_news_pages",
    )
    coverage_district = models.ForeignKey(
        "geography.District",
        verbose_name="Distrito",
        on_delete=models.PROTECT,
        related_name="covered_news_pages",
        null=True,
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
                FieldPanel("coverage_department"),
                FieldPanel(
                    "coverage_district",
                    widget=DependentDistrictWidget(
                        department_field="coverage_department"
                    ),
                ),
            ],
            heading="Cobertura",
        ),
        FieldPanel("publication_date"),
        FieldPanel("tags"),
        FieldPanel("school"),
        InlinePanel(
            "attributions",
            label="Autoría y créditos",
            help_text=ATTRIBUTION_HELP,
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

    def clean(self) -> None:
        super().clean()
        if (
            self.coverage_district_id
            and self.coverage_department_id
            and self.coverage_district.province.department_id
            != self.coverage_department_id
        ):
            raise ValidationError(
                {
                    "coverage_district": (
                        "El distrito debe pertenecer al departamento de cobertura."
                    )
                }
            )

    @cached_property
    def taxonomy(self):
        from .taxonomy import NewsTaxonomy

        return NewsTaxonomy.from_page(self)

    def get_sitemap_urls(self, request=None):
        if effective_noindex(self) or not canonical_is_self(self, request):
            return []
        return super().get_sitemap_urls(request=request)

    @property
    def public_attributions(self):
        return self._public_attribution_rows()

    @property
    def author_attributions(self):
        return [
            attribution
            for attribution in self._public_attribution_rows()
            if attribution.kind == NewsPageAttribution.Kind.AUTHOR
        ]

    def _public_attribution_rows(self):
        if hasattr(self, "public_attribution_rows"):
            return self.public_attribution_rows
        return list(
            self.attributions.filter(
                kind__in=(
                    NewsPageAttribution.Kind.AUTHOR,
                    NewsPageAttribution.Kind.PUBLIC_CREDIT,
                )
            )
            .select_related("author_profile__photo")
            .order_by("sort_order")
        )

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
            ),
        ]
        verbose_name = "Clasificación de noticia"
        verbose_name_plural = "Clasificaciones de noticia"

    def __str__(self) -> str:
        return str(self.section)


class NewsPageAttribution(Orderable):
    class Kind(models.TextChoices):
        AUTHOR = "AUTHOR", "Autor público"
        PUBLIC_CREDIT = "PUBLIC_CREDIT", "Firma pública"
        INTERNAL_CONTRIBUTOR = "INTERNAL_CONTRIBUTOR", "Colaborador interno"

    page = ParentalKey(
        NewsPage,
        related_name="attributions",
        on_delete=models.CASCADE,
    )
    kind = models.CharField("Tipo", max_length=24, choices=Kind.choices)
    author_profile = models.ForeignKey(
        AuthorProfile,
        verbose_name="Perfil público de autor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="news_attributions",
    )
    display_name = models.CharField(
        "Firma pública",
        max_length=255,
        blank=True,
        help_text=(
            "Texto público elegido por el editor. No se deriva automáticamente "
            "de colaboradores internos, colegios ni usuarios."
        ),
    )
    minor_contributor = models.ForeignKey(
        MinorContributor,
        verbose_name="Colaborador menor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="news_attributions",
    )

    panels = [
        FieldPanel("kind"),
        HelpPanel(
            content=(
                "<p><strong>Autor público:</strong> visible públicamente y respaldado "
                "por un perfil público de autor.</p>"
                "<p><strong>Firma pública:</strong> texto público libre sin perfil.</p>"
                "<p><strong>Colaborador interno:</strong> solo para uso interno, nunca "
                "público; por sí solo no permite publicar.</p>"
                "<p>Cada autor, firma o colaborador corresponde a una fila "
                "separada.</p>"
            )
        ),
        FieldPanel("author_profile"),
        FieldPanel("display_name"),
        FieldPanel("minor_contributor"),
    ]

    class Meta(Orderable.Meta):
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        kind="AUTHOR",
                        author_profile__isnull=False,
                        display_name="",
                        minor_contributor__isnull=True,
                    )
                    | models.Q(
                        kind="PUBLIC_CREDIT",
                        author_profile__isnull=True,
                        display_name__gt="",
                        minor_contributor__isnull=True,
                    )
                    | models.Q(
                        kind="INTERNAL_CONTRIBUTOR",
                        author_profile__isnull=True,
                        display_name="",
                        minor_contributor__isnull=False,
                    )
                ),
                name="news_page_attribution_fields_match_kind",
            ),
            models.UniqueConstraint(
                fields=("page", "author_profile"),
                condition=models.Q(author_profile__isnull=False),
                name="unique_news_page_author_profile",
            ),
            models.UniqueConstraint(
                fields=("page", "minor_contributor"),
                condition=models.Q(minor_contributor__isnull=False),
                name="unique_news_page_minor_contributor",
            ),
        ]
        verbose_name = "Autoría o crédito de noticia"
        verbose_name_plural = "Autorías y créditos de noticia"

    def __str__(self) -> str:
        if self.kind == self.Kind.AUTHOR and self.author_profile_id:
            return str(self.author_profile)
        if self.kind == self.Kind.INTERNAL_CONTRIBUTOR and self.minor_contributor_id:
            return str(self.minor_contributor)
        return self.display_name

    def clean(self) -> None:
        super().clean()
        errors = {}
        if self.kind == self.Kind.AUTHOR:
            if not self.author_profile_id:
                errors["author_profile"] = "Selecciona un perfil público de autor."
            if self.display_name.strip():
                errors["display_name"] = "La firma pública solo se usa para ese tipo."
            if self.minor_contributor_id:
                errors["minor_contributor"] = (
                    "El colaborador interno solo se usa para ese tipo."  # noqa: E501
                )
        elif self.kind == self.Kind.PUBLIC_CREDIT:
            if not self.display_name.strip():
                errors["display_name"] = "Escribe una firma pública."
            if self.author_profile_id:
                errors["author_profile"] = (
                    "El perfil público de autor solo se usa para ese tipo."  # noqa: E501
                )
            if self.minor_contributor_id:
                errors["minor_contributor"] = (
                    "El colaborador interno solo se usa para ese tipo."  # noqa: E501
                )
        elif self.kind == self.Kind.INTERNAL_CONTRIBUTOR:
            if not self.minor_contributor_id:
                errors["minor_contributor"] = "Selecciona un colaborador interno."
            if self.author_profile_id:
                errors["author_profile"] = (
                    "El perfil público de autor solo se usa para ese tipo."  # noqa: E501
                )
            if self.display_name.strip():
                errors["display_name"] = "La firma pública solo se usa para ese tipo."
        if errors:
            raise ValidationError(errors)
        if (
            self.kind == self.Kind.AUTHOR
            and self.author_profile is not None
            and not self.author_profile.is_active
        ):
            original_profile_id = None
            if self.pk:
                original_profile_id = (
                    type(self)
                    ._base_manager.using(self._state.db or "default")
                    .filter(pk=self.pk)
                    .values_list("author_profile_id", flat=True)
                    .first()
                )
            if original_profile_id != self.author_profile_id:
                raise ValidationError(
                    {
                        "author_profile": (
                            "Solo puedes asignar perfiles públicos de autor activos."
                        )
                    }
                )
