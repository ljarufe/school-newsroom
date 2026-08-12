"""Admin-only HTTP boundary for the smart-paste normalizer."""

import json

from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.news.access import FULL_EDITOR_PERMISSION
from apps.news.models import NewsPage
from apps.news.smart_paste import normalize_paste

SMART_PASTE_MAX_SOURCE_LENGTH = 1_000_000


@require_POST
@permission_required(FULL_EDITOR_PERMISSION, raise_exception=True)
def normalize_smart_paste(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "No se pudo leer el contenido pegado."},
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {"error": "El contenido pegado no tiene un formato válido."},
            status=400,
        )

    html_source = payload.get("html", "")
    plain_text = payload.get("text", "")
    if not isinstance(html_source, str) or not isinstance(plain_text, str):
        return JsonResponse(
            {"error": "El contenido pegado no tiene un formato válido."},
            status=400,
        )
    if len(html_source) + len(plain_text) > SMART_PASTE_MAX_SOURCE_LENGTH:
        return JsonResponse(
            {
                "error": (
                    "La nota pegada es demasiado extensa. Divídela en partes más "
                    "pequeñas e inténtalo de nuevo."
                )
            },
            status=400,
        )

    normalized = normalize_paste(
        html_source=html_source,
        plain_text=plain_text,
    )
    response_payload = normalized.as_dict()
    body_block = NewsPage._meta.get_field("body").stream_block
    for response_block, normalized_block in zip(
        response_payload["blocks"],
        normalized.blocks,
        strict=True,
    ):
        child_block = body_block.child_blocks[normalized_block.block_type]
        response_block["value"] = child_block.get_form_state(
            child_block.to_python(normalized_block.value)
        )

    return JsonResponse(response_payload)
