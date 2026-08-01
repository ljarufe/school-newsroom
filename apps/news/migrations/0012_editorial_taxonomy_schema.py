import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0011_alter_newspage_body"),
    ]

    operations = [
        migrations.AddField(
            model_name="newssection",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Déjalo vacío para crear una sección principal. Una subsección "
                    "no puede contener otras subsecciones."
                ),
                limit_choices_to={"parent__isnull": True},
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subsections",
                to="news.newssection",
                verbose_name="Sección principal",
            ),
        ),
        migrations.AlterModelOptions(
            name="newssection",
            options={
                "ordering": ["sort_order", "name", "pk"],
                "verbose_name": "Sección editorial",
                "verbose_name_plural": "Secciones editoriales",
            },
        ),
        migrations.AlterField(
            model_name="newspage",
            name="section",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="news_pages",
                to="news.newssection",
                verbose_name="Sección",
            ),
        ),
        migrations.CreateModel(
            name="NewsPageSection",
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
                (
                    "page",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="section_assignments",
                        to="news.newspage",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="news_page_assignments",
                        to="news.newssection",
                        verbose_name="Sección o subsección",
                    ),
                ),
            ],
            options={
                "verbose_name": "Clasificación de noticia",
                "verbose_name_plural": "Clasificaciones de noticia",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("page", "section"),
                        name="unique_news_page_section",
                    )
                ],
            },
        ),
    ]
