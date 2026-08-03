import math
import re

from .content import ContentSnapshot, count_words

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

ReadabilityCheck = tuple[str, str, str]


def _check(status: str, label: str, explanation: str) -> ReadabilityCheck:
    return status, label, explanation


def _max_section_words(snapshot: ContentSnapshot) -> int:
    maximum = 0
    current = 0
    for event in snapshot.events:
        if event.kind == "heading":
            maximum = max(maximum, current)
            current = 0
        else:
            current += count_words(event.text)
    return max(maximum, current)


def readability_checks(snapshot: ContentSnapshot) -> tuple[ReadabilityCheck, ...]:
    checks: list[ReadabilityCheck] = []
    if snapshot.text:
        checks.append(
            _check(
                "good",
                "Texto del artículo",
                "El artículo contiene prosa analizable.",
            ),
        )
    else:
        checks.append(
            _check(
                "problem",
                "Texto del artículo",
                "Añade texto al cuerpo de la noticia.",
            ),
        )

    paragraph_lengths = [count_words(paragraph) for paragraph in snapshot.paragraphs]
    longest_paragraph = max(paragraph_lengths, default=0)
    if longest_paragraph > 250:
        checks.append(
            _check(
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
            _check(
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
            _check(
                "good",
                "Longitud de párrafos",
                "Los párrafos están dentro del rango orientativo.",
            ),
        )
    else:
        checks.append(
            _check(
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
            _check(
                "not_applicable",
                "Longitud de oraciones",
                "No hay oraciones para analizar.",
            ),
        )
    elif long_ratio > 0.5:
        checks.append(
            _check(
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
            _check(
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
            _check(
                "good",
                "Longitud de oraciones",
                "La proporción de oraciones largas es moderada.",
            ),
        )

    if snapshot.word_count < 300:
        checks.append(
            _check(
                "not_applicable",
                "Uso de subtítulos",
                "La recomendación se aplica a artículos de 300 palabras o más.",
            ),
        )
    elif snapshot.headings:
        checks.append(
            _check(
                "good",
                "Uso de subtítulos",
                "El artículo largo utiliza subtítulos.",
            ),
        )
    else:
        checks.append(
            _check(
                "warning",
                "Uso de subtítulos",
                "Añade al menos un H2, H3 o H4 para orientar la lectura.",
            ),
        )

    largest_section = _max_section_words(snapshot)
    if not snapshot.text:
        checks.append(
            _check(
                "not_applicable",
                "Bloques de texto",
                "No hay texto para analizar.",
            ),
        )
    elif largest_section > 500:
        checks.append(
            _check(
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
            _check(
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
            _check(
                "good",
                "Bloques de texto",
                "La prosa está distribuida en bloques manejables.",
            ),
        )
    return tuple(checks)
