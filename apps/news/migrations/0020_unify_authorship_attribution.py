from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


def migrate_legacy_attributions(apps, schema_editor):
    """Copy legacy children in their stable per-relation editorial order."""
    NewsPage = apps.get_model("news", "NewsPage")
    NewsPageAttribution = apps.get_model("news", "NewsPageAttribution")
    NewsPagePublicCredit = apps.get_model("news", "NewsPagePublicCredit")
    NewsPageContributor = apps.get_model("news", "NewsPageContributor")
    db_alias = schema_editor.connection.alias

    for page_id in NewsPage.objects.using(db_alias).order_by("pk").values_list(
        "pk", flat=True
    ):
        sort_order = 0
        for credit in NewsPagePublicCredit.objects.using(db_alias).filter(
            page_id=page_id
        ).order_by("sort_order", "pk"):
            NewsPageAttribution.objects.using(db_alias).create(
                page_id=page_id,
                kind="PUBLIC_CREDIT",
                display_name=credit.display_name,
                sort_order=sort_order,
            )
            sort_order += 1
        for contributor in NewsPageContributor.objects.using(db_alias).filter(
            page_id=page_id
        ).order_by("sort_order", "pk"):
            NewsPageAttribution.objects.using(db_alias).create(
                page_id=page_id,
                kind="INTERNAL_CONTRIBUTOR",
                minor_contributor_id=contributor.contributor_id,
                sort_order=sort_order,
            )
            sort_order += 1


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0019_finalize_normalized_geography"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(max_length=160, verbose_name="Nombre público")),
                ("slug", models.SlugField(max_length=160, unique=True, verbose_name="Slug")),
                ("bio", models.TextField(blank=True, verbose_name="Biografía")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="Correo público")),
                ("position", models.CharField(blank=True, max_length=160, verbose_name="Cargo")),
                ("work_url", models.URLField(blank=True, verbose_name="URL de trabajo")),
                ("is_active", models.BooleanField(default=True, help_text="Desactiva el perfil para conservar su historial sin ofrecerlo en nuevas autorías.", verbose_name="Activo para nuevas autorías")),
                ("minor_contributor", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="author_profile", to="news.minorcontributor", verbose_name="Colaborador menor relacionado")),
                ("photo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="author_profiles", to="wagtailimages.image", verbose_name="Foto")),
                ("user", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="author_profile", to=settings.AUTH_USER_MODEL, verbose_name="Usuario interno relacionado")),
            ],
            options={
                "verbose_name": "Perfil público de autor",
                "verbose_name_plural": "Perfiles públicos de autor",
                "ordering": ["display_name", "pk"],
            },
        ),
        migrations.CreateModel(
            name="NewsPageAttribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                ("kind", models.CharField(choices=[("AUTHOR", "Autor público"), ("PUBLIC_CREDIT", "Firma pública"), ("INTERNAL_CONTRIBUTOR", "Colaborador interno")], max_length=24, verbose_name="Tipo")),
                ("display_name", models.CharField(blank=True, help_text="Texto público elegido por el editor. No se deriva automáticamente de colaboradores internos, colegios ni usuarios.", max_length=255, verbose_name="Firma pública")),
                ("author_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="news_attributions", to="news.authorprofile", verbose_name="Perfil público de autor")),
                ("minor_contributor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="news_attributions", to="news.minorcontributor", verbose_name="Colaborador menor")),
                ("page", modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name="attributions", to="news.newspage")),
            ],
            options={
                "verbose_name": "Autoría o crédito de noticia",
                "verbose_name_plural": "Autorías y créditos de noticia",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="authorprofile",
            constraint=models.CheckConstraint(condition=~(models.Q(("user__isnull", False), ("minor_contributor__isnull", False))), name="author_profile_internal_identity_is_exclusive"),
        ),
        migrations.AddConstraint(
            model_name="newspageattribution",
            constraint=models.CheckConstraint(condition=models.Q(("author_profile__isnull", False), ("display_name", ""), ("kind", "AUTHOR"), ("minor_contributor__isnull", True)) | models.Q(("author_profile__isnull", True), ("display_name__gt", ""), ("kind", "PUBLIC_CREDIT"), ("minor_contributor__isnull", True)) | models.Q(("author_profile__isnull", True), ("display_name", ""), ("kind", "INTERNAL_CONTRIBUTOR"), ("minor_contributor__isnull", False)), name="news_page_attribution_fields_match_kind"),
        ),
        migrations.AddConstraint(
            model_name="newspageattribution",
            constraint=models.UniqueConstraint(condition=models.Q(("author_profile__isnull", False)), fields=("page", "author_profile"), name="unique_news_page_author_profile"),
        ),
        migrations.AddConstraint(
            model_name="newspageattribution",
            constraint=models.UniqueConstraint(condition=models.Q(("minor_contributor__isnull", False)), fields=("page", "minor_contributor"), name="unique_news_page_minor_contributor"),
        ),
        migrations.RunPython(migrate_legacy_attributions, migrations.RunPython.noop),
        migrations.DeleteModel(name="NewsPagePublicCredit"),
        migrations.DeleteModel(name="NewsPageContributor"),
    ]
