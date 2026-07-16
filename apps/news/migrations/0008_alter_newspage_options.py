from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0007_newspage_featured_image_alt_text_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="newspage",
            options={
                "permissions": [
                    (
                        "access_full_editorial_surfaces",
                        "Puede acceder a todas las superficies editoriales del MVP",
                    ),
                    (
                        "access_seo_editorial_surface",
                        "Puede acceder a la superficie editorial SEO del MVP",
                    ),
                ],
                "verbose_name": "Noticia",
                "verbose_name_plural": "Noticias",
            },
        ),
    ]
