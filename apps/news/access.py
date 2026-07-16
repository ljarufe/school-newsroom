DIRECTOR_GROUP_NAME = "Director/editor"
SEO_CURATOR_GROUP_NAME = "Curador SEO"

FULL_EDITOR_PERMISSION = "news.access_full_editorial_surfaces"
SEO_EDITOR_PERMISSION = "news.access_seo_editorial_surface"

WORKFLOW_NAME = "Revisión editorial"
LEGACY_WORKFLOW_NAME = "Revisión editorial MVP"
SEO_TASK_NAME = "Revisión SEO"
FINAL_REVIEW_TASK_NAME = "Revisión editorial final"

NATIVE_SEO_FIELD_NAMES = frozenset(
    {
        "slug",
        "seo_title",
        "search_description",
    }
)

NEWS_SEO_FIELD_NAMES = NATIVE_SEO_FIELD_NAMES | {
    "focus_keyphrase",
    "og_title",
    "og_description",
    "og_image",
    "og_image_caption",
    "og_image_alt_text",
    "og_image_credit",
    "canonical_url",
    "seo_noindex",
}
