from django.db import models

CAPTION_LABEL = "Pie de foto"
ALT_TEXT_LABEL = "Texto alternativo"
CREDIT_LABEL = "Crédito de imagen"

ALT_TEXT_HELP_TEXT = "Describe el sentido contextual de esta imagen en la noticia."
CREDIT_HELP_TEXT = "Opcional. Indica la fuente o autoría pública de la imagen."

REQUIRED_METADATA_PARTS = (
    ("caption", CAPTION_LABEL.lower()),
    ("alt_text", ALT_TEXT_LABEL.lower()),
)


def effective_text(value) -> str:
    return str(value or "").strip()


def contextual_metadata_field(part: str) -> models.CharField:
    field_options = {
        "caption": {
            "verbose_name": CAPTION_LABEL,
            "max_length": 500,
        },
        "alt_text": {
            "verbose_name": ALT_TEXT_LABEL,
            "max_length": 500,
            "help_text": ALT_TEXT_HELP_TEXT,
        },
        "credit": {
            "verbose_name": CREDIT_LABEL,
            "max_length": 255,
            "help_text": CREDIT_HELP_TEXT,
        },
    }
    try:
        options = field_options[part]
    except KeyError as exc:
        raise ValueError(f"Unknown image metadata part: {part}") from exc
    return models.CharField(blank=True, **options)
