from django.db import migrations, models


def clear_minor_profile_emails(apps, schema_editor):
    """Remove legacy public email from minor-linked public profiles."""
    AuthorProfile = apps.get_model("news", "AuthorProfile")
    AuthorProfile.objects.using(schema_editor.connection.alias).filter(
        minor_contributor__isnull=False
    ).exclude(email="").update(email="")


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0020_unify_authorship_attribution"),
    ]

    operations = [
        migrations.RunPython(clear_minor_profile_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="authorprofile",
            constraint=models.CheckConstraint(
                condition=models.Q(minor_contributor__isnull=True) | models.Q(email=""),
                name="author_profile_minor_email_is_empty",
            ),
        ),
    ]
