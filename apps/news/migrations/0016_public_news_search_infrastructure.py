from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0015_newspagerelatedkeyphrase_and_more"),
        ("wagtailsearch", "0010_add_text_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE EXTENSION IF NOT EXISTS unaccent;
                CREATE EXTENSION IF NOT EXISTS pg_trgm;

                CREATE OR REPLACE FUNCTION f_unaccent(text)
                RETURNS text
                LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
                $function$
                    SELECT public.unaccent('public.unaccent', $1)
                $function$;

                CREATE TEXT SEARCH CONFIGURATION school_newsroom_es (COPY = spanish);
                ALTER TEXT SEARCH CONFIGURATION school_newsroom_es
                    ALTER MAPPING FOR asciiword, word, hword, hword_part,
                    asciihword, hword_asciipart
                    WITH unaccent, spanish_stem;

                CREATE INDEX news_archive_title_text_unaccent_trgm
                    ON wagtailsearch_indexentry
                    USING gin (f_unaccent(title_text) gin_trgm_ops);
                CREATE INDEX news_archive_body_text_unaccent_trgm
                    ON wagtailsearch_indexentry
                    USING gin (f_unaccent(body_text) gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS news_archive_body_text_unaccent_trgm;
                DROP INDEX IF EXISTS news_archive_title_text_unaccent_trgm;
                DROP TEXT SEARCH CONFIGURATION IF EXISTS school_newsroom_es;
                DROP FUNCTION IF EXISTS f_unaccent(text);
                DROP EXTENSION IF EXISTS pg_trgm;
                DROP EXTENSION IF EXISTS unaccent;
            """,
        ),
    ]
