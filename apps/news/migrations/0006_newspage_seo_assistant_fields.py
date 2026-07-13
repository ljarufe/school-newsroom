import apps.news.seo_metadata
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0005_alter_newspage_body"),
    ]

    operations = [
        migrations.AddField(
            model_name="newspage",
            name="canonical_url",
            field=models.URLField(
                blank=True,
                help_text="Déjala vacía para usar la URL pública de esta noticia. Usa una URL distinta sólo cuando otra versión deba ser la principal.",
                max_length=2048,
                validators=[apps.news.seo_metadata.validate_canonical_url],
                verbose_name="URL canonical",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="focus_keyphrase",
            field=models.CharField(
                blank=True,
                help_text="Frase exacta principal para el análisis SEO. No bloquea la publicación.",
                max_length=255,
                verbose_name="Frase clave objetivo",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="og_description",
            field=models.TextField(
                blank=True,
                help_text="Si queda vacía, se usa la descripción meta o el resumen de la noticia.",
                max_length=500,
                verbose_name="Descripción para redes sociales",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="og_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Si queda vacía, se usa la imagen destacada.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Imagen para redes sociales",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="og_title",
            field=models.CharField(
                blank=True,
                help_text="Si queda vacío, se usa el título SEO o el título de la noticia.",
                max_length=255,
                verbose_name="Título para redes sociales",
            ),
        ),
        migrations.AddField(
            model_name="newspage",
            name="seo_noindex",
            field=models.BooleanField(
                default=False,
                help_text="Solicita a los buscadores que no indexen esta noticia. No impide que la página sea visitada ni bloquea su rastreo.",
                verbose_name="Excluir de los resultados de búsqueda",
            ),
        ),
    ]
