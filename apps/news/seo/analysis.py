from dataclasses import dataclass
from urllib.parse import urlsplit

from ..image_metadata import effective_text
from .content import ContentSnapshot, LinkInfo, extract_content
from .keyphrases import (
    contains_exact_phrase,
    keyphrase_usage,
    normalize_for_match,
)
from .readability import readability_checks


@dataclass(frozen=True)
class CheckResult:
    status: str
    label: str
    explanation: str


@dataclass(frozen=True)
class AnalysisResult:
    seo_checks: tuple[CheckResult, ...]
    readability_checks: tuple[CheckResult, ...]
    overall_status: str
    overall_label: str


def _result(status: str, label: str, explanation: str) -> CheckResult:
    return CheckResult(status=status, label=label, explanation=explanation)


def _image_metadata_check(
    *,
    image,
    caption,
    alt_text,
    label: str,
    missing_image_explanation: str,
    complete_explanation: str,
) -> CheckResult:
    if not image:
        return _result("problem", label, missing_image_explanation)

    missing_parts = []
    if not effective_text(caption):
        missing_parts.append("pie de foto")
    if not effective_text(alt_text):
        missing_parts.append("texto alternativo")
    if missing_parts:
        return _result(
            "problem",
            label,
            f"Completa {', '.join(missing_parts)} para este uso de la imagen.",
        )
    return _result("good", label, complete_explanation)


def _keyphrase_location_check(
    keyphrase: str,
    value: str,
    *,
    label: str,
    missing_status: str,
    slug: bool = False,
) -> CheckResult:
    if not normalize_for_match(keyphrase):
        return _result(
            "not_applicable",
            label,
            "Añade una frase clave objetivo para activar esta comprobación.",
        )
    if contains_exact_phrase(value, keyphrase, slug=slug):
        return _result("good", label, "La frase clave aparece en este elemento.")
    return _result(
        missing_status,
        label,
        "La frase clave exacta no aparece en este elemento.",
    )


def _title_length_check(title: str) -> CheckResult:
    length = len(title)
    if length == 0:
        return _result(
            "problem",
            "Longitud del título SEO",
            "Falta el título SEO efectivo.",
        )
    if 30 <= length <= 60:
        return _result("good", "Longitud del título SEO", f"Tiene {length} caracteres.")
    if length <= 70:
        return _result(
            "warning",
            "Longitud del título SEO",
            f"Tiene {length} caracteres; el rango orientativo es de 30 a 60.",
        )
    return _result(
        "problem",
        "Longitud del título SEO",
        f"Tiene {length} caracteres; supera el máximo orientativo de 70.",
    )


def _description_length_check(description: str) -> CheckResult:
    length = len(description)
    if length == 0:
        return _result(
            "problem",
            "Longitud de la descripción meta",
            "Falta la descripción meta efectiva.",
        )
    if 120 <= length <= 160:
        return _result(
            "good",
            "Longitud de la descripción meta",
            f"Tiene {length} caracteres.",
        )
    if length <= 180:
        return _result(
            "warning",
            "Longitud de la descripción meta",
            f"Tiene {length} caracteres; el rango orientativo es de 120 a 160.",
        )
    return _result(
        "problem",
        "Longitud de la descripción meta",
        f"Tiene {length} caracteres; supera el máximo orientativo de 180.",
    )


def _word_count_check(word_count: int) -> CheckResult:
    if word_count < 150:
        return _result(
            "problem",
            "Extensión del artículo",
            f"El cuerpo tiene {word_count} palabras; se recomiendan al menos 300.",
        )
    if word_count < 300:
        return _result(
            "warning",
            "Extensión del artículo",
            f"El cuerpo tiene {word_count} palabras; se recomiendan al menos 300.",
        )
    return _result(
        "good",
        "Extensión del artículo",
        f"El cuerpo tiene {word_count} palabras.",
    )


def _keyphrase_overuse_check(
    keyphrase: str,
    snapshot: ContentSnapshot,
) -> CheckResult:
    if not normalize_for_match(keyphrase) or not snapshot.word_count:
        return _result(
            "not_applicable",
            "Uso de la frase clave",
            "Se necesita una frase clave y texto para calcular su uso.",
        )
    occurrences, rate = keyphrase_usage(
        snapshot.text,
        keyphrase,
        snapshot.word_count,
    )
    if occurrences >= 6 and rate > 5:
        return _result(
            "problem",
            "Uso de la frase clave",
            (
                f"Aparece {occurrences} veces ({rate:.1f} por cada 100 "
                "palabras); puede resultar repetitiva."
            ),
        )
    if occurrences >= 4 and rate > 3:
        return _result(
            "warning",
            "Uso de la frase clave",
            (
                f"Aparece {occurrences} veces ({rate:.1f} por cada 100 "
                "palabras); revisa la repetición."
            ),
        )
    return _result(
        "good",
        "Uso de la frase clave",
        f"Aparece {occurrences} veces y no muestra sobreuso evidente.",
    )


def _classify_links(
    links: list[LinkInfo],
    site_hostname: str,
) -> tuple[bool, bool]:
    has_internal = False
    has_external = False
    normalized_site_hostname = site_hostname.casefold().strip()

    for link in links:
        if link.linktype == "page":
            has_internal = True
            continue
        if link.linktype == "document":
            continue
        href = link.href.strip()
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue
        parsed = urlsplit(href)
        if not parsed.scheme and not parsed.netloc:
            has_internal = True
        elif parsed.scheme in {"http", "https"}:
            if normalized_site_hostname and parsed.hostname:
                if parsed.hostname.casefold() == normalized_site_hostname:
                    has_internal = True
                else:
                    has_external = True
            else:
                has_external = True
    return has_internal, has_external


def _seo_checks(
    page,
    snapshot: ContentSnapshot,
    site_hostname: str,
) -> tuple[CheckResult, ...]:
    keyphrase = (page.focus_keyphrase or "").strip()
    seo_title = (page.seo_title or "").strip()
    meta_description = (page.search_description or "").strip()
    introduction = snapshot.introduction

    checks: list[CheckResult] = []
    if keyphrase:
        checks.append(
            _result("good", "Frase clave objetivo", "La frase clave está configurada."),
        )
    else:
        checks.append(
            _result(
                "problem",
                "Frase clave objetivo",
                "Añade una frase clave objetivo para completar el análisis.",
            ),
        )
    checks.extend(
        [
            _keyphrase_location_check(
                keyphrase,
                seo_title,
                label="Frase clave en el título SEO",
                missing_status="problem",
            ),
            _keyphrase_location_check(
                keyphrase,
                page.slug or "",
                label="Frase clave en la URL",
                missing_status="warning",
                slug=True,
            ),
            _keyphrase_location_check(
                keyphrase,
                meta_description,
                label="Frase clave en la descripción meta",
                missing_status="problem",
            ),
            _keyphrase_location_check(
                keyphrase,
                introduction,
                label="Frase clave en la introducción",
                missing_status="warning",
            ),
        ],
    )
    if not keyphrase:
        checks.append(
            _result(
                "not_applicable",
                "Frase clave en subtítulos",
                "Añade una frase clave objetivo para activar esta comprobación.",
            ),
        )
    elif not snapshot.headings:
        checks.append(
            _result(
                "not_applicable",
                "Frase clave en subtítulos",
                "El artículo todavía no contiene subtítulos H2, H3 o H4.",
            ),
        )
    else:
        checks.append(
            _keyphrase_location_check(
                keyphrase,
                " ".join(snapshot.headings),
                label="Frase clave en subtítulos",
                missing_status="warning",
            ),
        )
    checks.extend(
        [
            _keyphrase_location_check(
                keyphrase,
                snapshot.text,
                label="Frase clave en el cuerpo",
                missing_status="problem",
            ),
            _keyphrase_overuse_check(keyphrase, snapshot),
            _title_length_check(seo_title),
            _description_length_check(meta_description),
            _word_count_check(snapshot.word_count),
        ],
    )
    featured_image = getattr(page, "featured_image", None)
    featured_caption = getattr(page, "featured_image_caption", "")
    featured_alt_text = getattr(page, "featured_image_alt_text", "")
    checks.append(
        _image_metadata_check(
            image=featured_image,
            caption=featured_caption,
            alt_text=featured_alt_text,
            label="Imagen destacada",
            missing_image_explanation=(
                "Añade una imagen destacada para la noticia y su vista social."
            ),
            complete_explanation=(
                "La imagen destacada tiene pie de foto y texto alternativo."
            ),
        ),
    )
    og_image = getattr(page, "og_image", None)
    if og_image:
        social_caption = getattr(page, "og_image_caption", "")
        social_alt_text = getattr(page, "og_image_alt_text", "")
        social_explanation = (
            "La imagen social propia tiene pie de foto y texto alternativo."
        )
    else:
        social_caption = featured_caption
        social_alt_text = featured_alt_text
        social_explanation = (
            "La imagen social usa la imagen destacada y su metadata contextual."
        )
    checks.append(
        _image_metadata_check(
            image=og_image or featured_image,
            caption=social_caption,
            alt_text=social_alt_text,
            label="Metadata de imagen social",
            missing_image_explanation=(
                "Añade una imagen social o una imagen destacada como fallback."
            ),
            complete_explanation=social_explanation,
        ),
    )
    if not snapshot.body_image_alts:
        checks.append(
            _result(
                "not_applicable",
                "Texto alternativo en imágenes del cuerpo",
                "El cuerpo no contiene imágenes.",
            ),
        )
    elif all(alt.strip() for alt in snapshot.body_image_alts):
        checks.append(
            _result(
                "good",
                "Texto alternativo en imágenes del cuerpo",
                "Todas las imágenes del cuerpo tienen texto alternativo.",
            ),
        )
    else:
        checks.append(
            _result(
                "problem",
                "Texto alternativo en imágenes del cuerpo",
                "Al menos una imagen del cuerpo no tiene texto alternativo efectivo.",
            ),
        )

    if not snapshot.text:
        checks.extend(
            [
                _result(
                    "not_applicable",
                    "Enlace interno",
                    "Se necesita texto para revisar enlaces.",
                ),
                _result(
                    "not_applicable",
                    "Enlace externo",
                    "Se necesita texto para revisar enlaces.",
                ),
            ],
        )
    else:
        has_internal, has_external = _classify_links(snapshot.links, site_hostname)
        checks.extend(
            [
                _result(
                    "good" if has_internal else "warning",
                    "Enlace interno",
                    "El cuerpo contiene un enlace interno."
                    if has_internal
                    else "Considera enlazar otra página relevante del sitio.",
                ),
                _result(
                    "good" if has_external else "warning",
                    "Enlace externo",
                    "El cuerpo contiene un enlace externo."
                    if has_external
                    else (
                        "Considera citar una fuente externa relevante cuando "
                        "corresponda."
                    ),
                ),
            ],
        )
    return tuple(checks)


def analyze_page(page, *, site_hostname: str = "") -> AnalysisResult:
    snapshot = extract_content(page.body)
    seo_checks = _seo_checks(page, snapshot, site_hostname)
    readability = tuple(
        _result(status, label, explanation)
        for status, label, explanation in readability_checks(snapshot)
    )
    incomplete = not all(
        (
            (page.focus_keyphrase or "").strip(),
            (page.seo_title or "").strip(),
            (page.search_description or "").strip(),
            snapshot.text,
        ),
    )
    if incomplete:
        overall_status = "problem"
        overall_label = "Incompleto"
    elif any(
        check.status in {"problem", "warning"} for check in (*seo_checks, *readability)
    ):
        overall_status = "warning"
        overall_label = "Necesita mejoras"
    else:
        overall_status = "good"
        overall_label = "Bueno"
    return AnalysisResult(
        seo_checks=seo_checks,
        readability_checks=readability,
        overall_status=overall_status,
        overall_label=overall_label,
    )
