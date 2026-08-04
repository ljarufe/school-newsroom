import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0014_remove_singular_section"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newspage",
            name="focus_keyphrase",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Frase exacta principal para el análisis SEO. No bloquea la "
                    "publicación."
                ),
                max_length=255,
                verbose_name="Frase clave principal",
            ),
        ),
        migrations.CreateModel(
            name="NewsPageRelatedKeyphrase",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                ("phrase", models.CharField(max_length=255, verbose_name="Frase relacionada")),
                (
                    "page",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="related_keyphrases",
                        to="news.newspage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Frase clave relacionada",
                "verbose_name_plural": "Frases clave relacionadas",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
    ]
