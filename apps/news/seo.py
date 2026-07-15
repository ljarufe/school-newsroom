import math
import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlsplit

from wagtail.rich_text import RichText

from .image_metadata import effective_text

WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class LinkInfo:
    href: str
    linktype: str = ""


@dataclass(frozen=True)
class ContentEvent:
    kind: str
    text: str


@dataclass
class ContentSnapshot:
    text: str = ""
    paragraphs: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    body_image_alts: list[str] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)
    events: list[ContentEvent] = field(default_factory=list)

    @property
    def introduction(self) -> str:
        return self.paragraphs[0] if self.paragraphs else ""

    @property
    def word_count(self) -> int:
        return count_words(self.text)


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


class _RichTextExtractor(HTMLParser):
    captured_tags = {"p": "paragraph", "li": "paragraph", "blockquote": "paragraph"}
    heading_tags = {"h2", "h3", "h4"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.all_text: list[str] = []
        self.paragraphs: list[str] = []
        self.headings: list[str] = []
        self.links: list[LinkInfo] = []
        self.events: list[ContentEvent] = []
        self._captures: list[tuple[str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.captured_tags or tag in self.heading_tags:
            self._captures.append((tag, []))
        if tag == "a":
            attributes = {name.lower(): value or "" for name, value in attrs}
            self.links.append(
                LinkInfo(
                    href=attributes.get("href", "").strip(),
                    linktype=attributes.get("linktype", "").strip().lower(),
                ),
            )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._captures) - 1, -1, -1):
            captured_tag, chunks = self._captures[index]
            if captured_tag != tag:
                continue
            del self._captures[index]
            text = normalize_whitespace(" ".join(chunks))
            if not text:
                return
            if tag in self.heading_tags:
                self.headings.append(text)
                self.events.append(ContentEvent("heading", text))
            else:
                self.paragraphs.append(text)
                self.events.append(ContentEvent("paragraph", text))
            return

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self._captures:
            self._captures[-1][1].append(data)


def normalize_whitespace(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip()


def normalize_for_match(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return normalize_whitespace(without_accents.casefold())


def normalize_slug_for_match(value: str) -> str:
    return normalize_for_match((value or "").replace("-", " ").replace("_", " "))


def contains_exact_phrase(value: str, phrase: str, *, slug: bool = False) -> bool:
    normalized_phrase = normalize_for_match(phrase)
    if not normalized_phrase:
        return False
    normalized_value = (
        normalize_slug_for_match(value) if slug else normalize_for_match(value)
    )
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)")
    return bool(pattern.search(normalized_value))


def count_exact_phrase(value: str, phrase: str) -> int:
    normalized_phrase = normalize_for_match(phrase)
    if not normalized_phrase:
        return 0
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)")
    return len(pattern.findall(normalize_for_match(value)))


def count_words(value: str) -> int:
    return len(WORD_RE.findall(value or ""))


def extract_content(body) -> ContentSnapshot:
    snapshot = ContentSnapshot()
    text_parts: list[str] = []

    if not body:
        return snapshot

    for child in body:
        if child.block_type == "paragraph":
            value = child.value
            source = value.source if isinstance(value, RichText) else str(value or "")
            parser = _RichTextExtractor()
            parser.feed(source)
            parser.close()
            visible_text = normalize_whitespace(" ".join(parser.all_text))
            if visible_text:
                text_parts.append(visible_text)
            snapshot.paragraphs.extend(parser.paragraphs)
            snapshot.headings.extend(parser.headings)
            snapshot.links.extend(parser.links)
            snapshot.events.extend(parser.events)
            if visible_text and not parser.events:
                snapshot.paragraphs.append(visible_text)
                snapshot.events.append(ContentEvent("paragraph", visible_text))
        elif child.block_type == "article_image":
            snapshot.body_image_alts.append(str(child.value.get("alt_text") or ""))

    snapshot.text = normalize_whitespace(" ".join(text_parts))
    return snapshot


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


def _keyphrase_overuse_check(keyphrase: str, snapshot: ContentSnapshot) -> CheckResult:
    if not normalize_for_match(keyphrase) or not snapshot.word_count:
        return _result(
            "not_applicable",
            "Uso de la frase clave",
            "Se necesita una frase clave y texto para calcular su uso.",
        )
    occurrences = count_exact_phrase(snapshot.text, keyphrase)
    rate = occurrences / snapshot.word_count * 100
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
    introduction = " ".join(
        value
        for value in ((page.summary or "").strip(), snapshot.introduction)
        if value
    )

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
                label="Frase clave en el resumen o introducción",
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


def _max_section_words(events: list[ContentEvent]) -> int:
    maximum = 0
    current = 0
    for event in events:
        if event.kind == "heading":
            maximum = max(maximum, current)
            current = 0
        else:
            current += count_words(event.text)
    return max(maximum, current)


def _readability_checks(snapshot: ContentSnapshot) -> tuple[CheckResult, ...]:
    checks: list[CheckResult] = []
    if snapshot.text:
        checks.append(
            _result(
                "good",
                "Texto del artículo",
                "El artículo contiene prosa analizable.",
            ),
        )
    else:
        checks.append(
            _result(
                "problem",
                "Texto del artículo",
                "Añade texto al cuerpo de la noticia.",
            ),
        )

    paragraph_lengths = [count_words(paragraph) for paragraph in snapshot.paragraphs]
    longest_paragraph = max(paragraph_lengths, default=0)
    if longest_paragraph > 250:
        checks.append(
            _result(
                "problem",
                "Longitud de párrafos",
                (
                    f"El párrafo más largo tiene {longest_paragraph} palabras; "
                    "conviene dividirlo."
                ),
            ),
        )
    elif longest_paragraph > 150:
        checks.append(
            _result(
                "warning",
                "Longitud de párrafos",
                (
                    f"El párrafo más largo tiene {longest_paragraph} palabras; "
                    "considera dividirlo."
                ),
            ),
        )
    elif snapshot.paragraphs:
        checks.append(
            _result(
                "good",
                "Longitud de párrafos",
                "Los párrafos están dentro del rango orientativo.",
            ),
        )
    else:
        checks.append(
            _result(
                "not_applicable",
                "Longitud de párrafos",
                "No hay párrafos para analizar.",
            ),
        )

    sentences = [
        sentence
        for sentence in SENTENCE_SPLIT_RE.split(snapshot.text)
        if count_words(sentence)
    ]
    long_sentences = [sentence for sentence in sentences if count_words(sentence) > 30]
    long_ratio = len(long_sentences) / len(sentences) if sentences else 0
    if not sentences:
        checks.append(
            _result(
                "not_applicable",
                "Longitud de oraciones",
                "No hay oraciones para analizar.",
            ),
        )
    elif long_ratio > 0.5:
        checks.append(
            _result(
                "problem",
                "Longitud de oraciones",
                (
                    f"{math.floor(long_ratio * 100)} % de las oraciones supera "
                    "30 palabras."
                ),
            ),
        )
    elif long_ratio > 0.25:
        checks.append(
            _result(
                "warning",
                "Longitud de oraciones",
                (
                    f"{math.floor(long_ratio * 100)} % de las oraciones supera "
                    "30 palabras."
                ),
            ),
        )
    else:
        checks.append(
            _result(
                "good",
                "Longitud de oraciones",
                "La proporción de oraciones largas es moderada.",
            ),
        )

    if snapshot.word_count < 300:
        checks.append(
            _result(
                "not_applicable",
                "Uso de subtítulos",
                "La recomendación se aplica a artículos de 300 palabras o más.",
            ),
        )
    elif snapshot.headings:
        checks.append(
            _result(
                "good",
                "Uso de subtítulos",
                "El artículo largo utiliza subtítulos.",
            ),
        )
    else:
        checks.append(
            _result(
                "warning",
                "Uso de subtítulos",
                "Añade al menos un H2, H3 o H4 para orientar la lectura.",
            ),
        )

    largest_section = _max_section_words(snapshot.events)
    if not snapshot.text:
        checks.append(
            _result(
                "not_applicable",
                "Bloques de texto",
                "No hay texto para analizar.",
            ),
        )
    elif largest_section > 500:
        checks.append(
            _result(
                "problem",
                "Bloques de texto",
                (
                    f"Hay una sección continua de {largest_section} palabras; "
                    "divídela con subtítulos."
                ),
            ),
        )
    elif largest_section > 300:
        checks.append(
            _result(
                "warning",
                "Bloques de texto",
                (
                    f"Hay una sección continua de {largest_section} palabras; "
                    "considera dividirla."
                ),
            ),
        )
    else:
        checks.append(
            _result(
                "good",
                "Bloques de texto",
                "La prosa está distribuida en bloques manejables.",
            ),
        )
    return tuple(checks)


def analyze_page(page, *, site_hostname: str = "") -> AnalysisResult:
    snapshot = extract_content(page.body)
    seo_checks = _seo_checks(page, snapshot, site_hostname)
    readability_checks = _readability_checks(snapshot)
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
        check.status in {"problem", "warning"}
        for check in (*seo_checks, *readability_checks)
    ):
        overall_status = "warning"
        overall_label = "Necesita mejoras"
    else:
        overall_status = "good"
        overall_label = "Bueno"
    return AnalysisResult(
        seo_checks=seo_checks,
        readability_checks=readability_checks,
        overall_status=overall_status,
        overall_label=overall_label,
    )
