from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0013_migrate_editorial_taxonomy"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="newspage",
            name="section",
        ),
    ]
