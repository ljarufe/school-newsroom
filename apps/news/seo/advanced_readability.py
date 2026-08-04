import importlib
import logging
import math
import threading
from dataclasses import dataclass

from .content import ContentSegment, normalize_whitespace
from .keyphrases import normalize_for_match
from .nlp import AnalyzedText, NlpToken

logger = logging.getLogger(__name__)

MAX_EVIDENCE_ITEMS = 3
MAX_EVIDENCE_CHARACTERS = 220
MATTR_WINDOW = 50
HYPHENATION_DICTIONARY = "es_ES"
AUTHORIZED_PROSE_KINDS = frozenset({"paragraph", "list", "quote"})
CLAUSE_DEPENDENCIES = frozenset(
    {"ROOT", "acl", "acl:relcl", "advcl", "ccomp", "conj", "xcomp"}
)
PASSIVE_PREDICATE_DEPENDENCIES = CLAUSE_DEPENDENCIES
PASSIVE_AUXILIARY_DEPENDENCIES = frozenset({"aux", "aux:pass"})

STATUS_LABELS = {
    "good": "Correcto",
    "improve": "Por mejorar",
    "informative": "Informativo",
    "not_applicable": "No aplica",
    "unavailable": "No disponible",
}

CONNECTOR_LEXICON = (
    (
        "Adición",
        (
            "además",
            "también",
            "asimismo",
            "incluso",
            "de igual manera",
            "por otra parte",
        ),
    ),
    (
        "Contraste o concesión",
        (
            "sin embargo",
            "no obstante",
            "en cambio",
            "por el contrario",
            "aunque",
            "aun así",
        ),
    ),
    ("Causa", ("porque", "ya que", "debido a", "puesto que")),
    (
        "Consecuencia",
        (
            "por eso",
            "por lo tanto",
            "por consiguiente",
            "en consecuencia",
            "así que",
        ),
    ),
    (
        "Orden o tiempo",
        (
            "primero",
            "en primer lugar",
            "después",
            "luego",
            "más tarde",
            "finalmente",
            "mientras tanto",
        ),
    ),
    (
        "Explicación o ejemplo",
        ("por ejemplo", "es decir", "en otras palabras"),
    ),
    ("Conclusión", ("en resumen", "en síntesis", "para concluir")),
)

FINDING_DEFINITIONS = (
    ("long-sentences", "Oraciones extensas con evidencia"),
    ("consecutive-openings", "Comienzos consecutivos"),
    ("connectors", "Uso de conectores"),
    ("periphrastic-passive", "Pasiva perifrástica"),
    ("syntactic-complexity", "Complejidad sintáctica"),
    ("lexical-density", "Densidad léxica"),
    ("lexical-diversity", "Diversidad léxica"),
    ("flesch-szigriszt", "Flesch-Szigriszt e INFLESZ"),
)


class HyphenationUnavailableError(RuntimeError):
    """The bundled Spanish hyphenation dictionary could not be initialized."""


@dataclass(frozen=True)
class AdvancedReadabilityEvidence:
    text: str
    location: str
    metric: str = ""


@dataclass(frozen=True)
class AdvancedReadabilityFinding:
    id: str
    status: str
    title: str
    explanation: str
    metric: str = ""
    value: float | None = None
    evidence: tuple[AdvancedReadabilityEvidence, ...] = ()
    locations: tuple[str, ...] = ()

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]


@dataclass(frozen=True)
class _SentenceRecord:
    order: int
    section_index: int
    segment: ContentSegment
    analyzed: AnalyzedText
    token_start: int
    token_end: int
    start: int
    end: int
    location: str

    @property
    def tokens(self) -> tuple[NlpToken, ...]:
        return self.analyzed.tokens[self.token_start : self.token_end]

    @property
    def words(self) -> tuple[NlpToken, ...]:
        return tuple(token for token in self.tokens if token.word)

    @property
    def content_tokens(self) -> tuple[NlpToken, ...]:
        return tuple(token for token in self.tokens if token.content)

    @property
    def text(self) -> str:
        return self.analyzed.text[self.start : self.end]


_HYPHENATION_LOCK = threading.Lock()
_HYPHENATOR = None
_HYPHENATION_ATTEMPTED = False
_HYPHENATION_ERROR = False
_HYPHENATION_LOAD_ATTEMPTS = 0


def _load_hyphenator():
    global _HYPHENATION_ATTEMPTED
    global _HYPHENATION_ERROR
    global _HYPHENATION_LOAD_ATTEMPTS
    global _HYPHENATOR

    if _HYPHENATION_ATTEMPTED:
        if _HYPHENATION_ERROR:
            raise HyphenationUnavailableError from None
        return _HYPHENATOR

    with _HYPHENATION_LOCK:
        if _HYPHENATION_ATTEMPTED:
            if _HYPHENATION_ERROR:
                raise HyphenationUnavailableError from None
            return _HYPHENATOR

        _HYPHENATION_LOAD_ATTEMPTS += 1
        try:
            pyphen_module = importlib.import_module("pyphen")
            hyphenator = pyphen_module.Pyphen(lang=HYPHENATION_DICTIONARY)
        except Exception as error:
            _HYPHENATION_ERROR = True
            _HYPHENATION_ATTEMPTED = True
            logger.error(
                "SEO syllabification initialization failed (dictionary=%s, error=%s).",
                HYPHENATION_DICTIONARY,
                type(error).__name__,
            )
            raise HyphenationUnavailableError from None

        _HYPHENATOR = hyphenator
        _HYPHENATION_ATTEMPTED = True
        return _HYPHENATOR


def reset_hyphenation_cache() -> None:
    """Reset process state for isolated tests; application code never retries."""

    global _HYPHENATION_ATTEMPTED
    global _HYPHENATION_ERROR
    global _HYPHENATION_LOAD_ATTEMPTS
    global _HYPHENATOR

    with _HYPHENATION_LOCK:
        _HYPHENATOR = None
        _HYPHENATION_ATTEMPTED = False
        _HYPHENATION_ERROR = False
        _HYPHENATION_LOAD_ATTEMPTS = 0


def hyphenation_load_attempts() -> int:
    return _HYPHENATION_LOAD_ATTEMPTS


def unavailable_advanced_readability(
    explanation: str = (
        "El análisis lingüístico no estuvo disponible para esta respuesta."
    ),
) -> tuple[AdvancedReadabilityFinding, ...]:
    return tuple(
        AdvancedReadabilityFinding(
            id=finding_id,
            status="unavailable",
            title=title,
            explanation=explanation,
        )
        for finding_id, title in FINDING_DEFINITIONS
    )


def _finding(
    finding_id: str,
    status: str,
    title: str,
    explanation: str,
    *,
    metric: str = "",
    value: float | None = None,
    evidence: tuple[AdvancedReadabilityEvidence, ...] = (),
) -> AdvancedReadabilityFinding:
    bounded_evidence = evidence[:MAX_EVIDENCE_ITEMS]
    return AdvancedReadabilityFinding(
        id=finding_id,
        status=status,
        title=title,
        explanation=explanation,
        metric=metric,
        value=value,
        evidence=bounded_evidence,
        locations=tuple(dict.fromkeys(item.location for item in bounded_evidence)),
    )


def _brief(value: str) -> str:
    text = normalize_whitespace(value)
    if len(text) <= MAX_EVIDENCE_CHARACTERS:
        return text
    return f"{text[: MAX_EVIDENCE_CHARACTERS - 1].rstrip()}…"


def _evidence(
    sentence: _SentenceRecord,
    metric: str = "",
) -> AdvancedReadabilityEvidence:
    return AdvancedReadabilityEvidence(
        text=_brief(sentence.text),
        location=sentence.location,
        metric=metric,
    )


def _sentence_records(
    analyzed_segments: tuple[tuple[ContentSegment, AnalyzedText], ...],
) -> tuple[_SentenceRecord, ...]:
    records = []
    section_index = 0
    kind_counts = {kind: 0 for kind in AUTHORIZED_PROSE_KINDS}
    kind_labels = {"paragraph": "Párrafo", "list": "Lista", "quote": "Cita"}
    for segment, analyzed in analyzed_segments:
        if segment.kind == "heading":
            section_index += 1
            continue
        if segment.kind not in AUTHORIZED_PROSE_KINDS:
            continue
        kind_counts[segment.kind] += 1
        location = (
            f"{kind_labels[segment.kind]} {kind_counts[segment.kind]} "
            f"({segment.reference})"
        )
        for sentence in analyzed.sentences:
            tokens = analyzed.tokens[sentence.token_start : sentence.token_end]
            if not any(token.word for token in tokens):
                continue
            records.append(
                _SentenceRecord(
                    order=len(records),
                    section_index=section_index,
                    segment=segment,
                    analyzed=analyzed,
                    token_start=sentence.token_start,
                    token_end=sentence.token_end,
                    start=sentence.start,
                    end=sentence.end,
                    location=location,
                )
            )
    return tuple(records)


def _long_sentences(
    sentences: tuple[_SentenceRecord, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[0][1]
    if not sentences:
        return _finding(
            "long-sentences",
            "not_applicable",
            title,
            "No hay oraciones analizables en la prosa autorizada del cuerpo.",
        )
    long_sentences = tuple(
        sentence for sentence in sentences if len(sentence.words) > 30
    )
    ratio = len(long_sentences) / len(sentences)
    percentage = math.floor(ratio * 100)
    prioritized = sorted(
        long_sentences,
        key=lambda sentence: (-len(sentence.words), sentence.order),
    )
    return _finding(
        "long-sentences",
        "improve" if ratio > 0.25 else "good",
        title,
        (
            "Revisa las oraciones de más de 30 palabras; el porcentaje se "
            "muestra truncado al entero inferior."
        ),
        metric=(
            f"{len(long_sentences)} de {len(sentences)} oraciones extensas "
            f"({percentage} %)."
        ),
        evidence=tuple(
            _evidence(sentence, f"{len(sentence.words)} palabras")
            for sentence in prioritized
        ),
    )


def _opening_signature(sentence: _SentenceRecord) -> tuple[str, ...]:
    return tuple(
        token.normalized_lemma
        for token in sentence.content_tokens[:2]
        if token.normalized_lemma
    )


def _consecutive_openings(
    sentences: tuple[_SentenceRecord, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[1][1]
    if len(sentences) < 3:
        return _finding(
            "consecutive-openings",
            "not_applicable",
            title,
            "Se necesitan al menos tres oraciones analizables.",
        )

    signatures = tuple(_opening_signature(sentence) for sentence in sentences)
    runs = []
    start = 0
    while start < len(sentences):
        signature = signatures[start]
        end = start + 1
        while (
            end < len(sentences)
            and signature
            and sentences[end].section_index == sentences[start].section_index
            and signatures[end] == signature
        ):
            end += 1
        if signature and end - start >= 3:
            runs.append((start, end, signature))
        start = end

    evidence = tuple(
        _evidence(
            sentences[start_index],
            (
                f"Firma «{' '.join(signature)}» · "
                f"{end_index - start_index} oraciones consecutivas"
            ),
        )
        for start_index, end_index, signature in runs
    )
    return _finding(
        "consecutive-openings",
        "improve" if runs else "good",
        title,
        (
            "Compara los dos primeros lemas de contenido de cada oración; "
            "sólo se señalan secuencias de tres o más."
        ),
        metric=(
            "1 secuencia problemática."
            if len(runs) == 1
            else f"{len(runs)} secuencias problemáticas."
        ),
        evidence=evidence,
    )


def _connector_definitions() -> tuple[tuple[tuple[str, ...], str, str], ...]:
    definitions = []
    for category, expressions in CONNECTOR_LEXICON:
        for expression in expressions:
            normalized = tuple(normalize_for_match(expression).split())
            definitions.append((normalized, category, expression))
    return tuple(sorted(definitions, key=lambda item: -len(item[0])))


_CONNECTOR_DEFINITIONS = _connector_definitions()


def _sentence_connectors(
    sentence: _SentenceRecord,
) -> tuple[tuple[str, str], ...]:
    normalized_tokens = tuple(
        token.normalized_text for token in sentence.tokens if token.word
    )
    matches = []
    index = 0
    while index < len(normalized_tokens):
        match = next(
            (
                (tokens, category, expression)
                for tokens, category, expression in _CONNECTOR_DEFINITIONS
                if normalized_tokens[index : index + len(tokens)] == tokens
            ),
            None,
        )
        if match is None:
            index += 1
            continue
        tokens, category, expression = match
        matches.append((category, expression))
        index += len(tokens)
    return tuple(matches)


def _connectors(
    sentences: tuple[_SentenceRecord, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[2][1]
    if len(sentences) < 5:
        return _finding(
            "connectors",
            "not_applicable",
            title,
            "Se necesitan al menos cinco oraciones analizables.",
        )

    detected = tuple(
        (sentence, matches)
        for sentence in sentences
        if (matches := _sentence_connectors(sentence))
    )
    ratio = len(detected) / len(sentences)
    percentage = math.floor(ratio * 100)
    if ratio < 0.10:
        status = "improve"
    elif ratio < 0.20:
        status = "informative"
    else:
        status = "good"
    detected_categories = {
        category for _sentence, matches in detected for category, _expression in matches
    }
    ordered_categories = tuple(
        category
        for category, _expressions in CONNECTOR_LEXICON
        if category in detected_categories
    )
    categories_metric = ", ".join(ordered_categories) or "ninguna"
    return _finding(
        "connectors",
        status,
        title,
        (
            "La proporción es orientativa y no implica que convenga insertar "
            "conectores de forma mecánica."
        ),
        metric=(
            f"{len(detected)} de {len(sentences)} oraciones ({percentage} %). "
            f"Categorías: {categories_metric}."
        ),
        evidence=tuple(
            _evidence(
                sentence,
                "Conectores: "
                + ", ".join(expression for _category, expression in matches),
            )
            for sentence, matches in detected
        ),
    )


def _passive_predicates(sentence: _SentenceRecord) -> tuple[NlpToken, ...]:
    predicates = []
    for token in sentence.tokens:
        if (
            token.pos != "VERB"
            or "VerbForm=Part" not in token.morphology
            or token.dependency not in PASSIVE_PREDICATE_DEPENDENCIES
        ):
            continue
        if any(
            candidate.head_index == token.index
            and candidate.pos == "AUX"
            and candidate.normalized_lemma == "ser"
            and candidate.dependency in PASSIVE_AUXILIARY_DEPENDENCIES
            for candidate in sentence.tokens
        ):
            predicates.append(token)
    return tuple(predicates)


def _periphrastic_passive(
    sentences: tuple[_SentenceRecord, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[3][1]
    if not sentences:
        return _finding(
            "periphrastic-passive",
            "not_applicable",
            title,
            "No hay oraciones analizables en la prosa autorizada del cuerpo.",
        )
    detected = tuple(
        (sentence, predicates)
        for sentence in sentences
        if (predicates := _passive_predicates(sentence))
    )
    ratio = len(detected) / len(sentences)
    percentage = math.floor(ratio * 100)
    if not detected:
        status = "good"
    elif len(detected) == 1 or ratio < 0.10:
        status = "informative"
    else:
        status = "improve"
    return _finding(
        "periphrastic-passive",
        status,
        title,
        (
            "La detección conservadora exige una forma de «ser» unida "
            "sintácticamente a un participio verbal."
        ),
        metric=(f"{len(detected)} de {len(sentences)} oraciones ({percentage} %)."),
        evidence=tuple(
            _evidence(
                sentence,
                "Participios detectados: "
                + ", ".join(predicate.text for predicate in predicates),
            )
            for sentence, predicates in detected
        ),
    )


def _clause_head_count(sentence: _SentenceRecord) -> int:
    return sum(
        token.dependency in CLAUSE_DEPENDENCIES
        and token.pos in {"AUX", "VERB"}
        and any(feature.startswith("VerbForm=") for feature in token.morphology)
        for token in sentence.tokens
    )


def _syntactic_complexity(
    sentences: tuple[_SentenceRecord, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[4][1]
    if len(sentences) < 3:
        return _finding(
            "syntactic-complexity",
            "not_applicable",
            title,
            "Se necesitan al menos tres oraciones analizables.",
        )
    complex_sentences = tuple(
        (sentence, count)
        for sentence in sentences
        if (count := _clause_head_count(sentence)) >= 3
    )
    ratio = len(complex_sentences) / len(sentences)
    percentage = math.floor(ratio * 100)
    if not complex_sentences:
        status = "good"
    elif ratio <= 0.20:
        status = "informative"
    else:
        status = "improve"
    return _finding(
        "syntactic-complexity",
        status,
        title,
        (
            "Es una estimación por cabezas de cláusula, no un análisis "
            "gramatical exhaustivo."
        ),
        metric=(
            f"{len(complex_sentences)} de {len(sentences)} oraciones "
            f"complejas ({percentage} %)."
        ),
        evidence=tuple(
            _evidence(sentence, f"{count} cabezas de cláusula estimadas")
            for sentence, count in complex_sentences
        ),
    )


def _lexical_density(
    words: tuple[NlpToken, ...],
    content_tokens: tuple[NlpToken, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[5][1]
    if len(words) < 50:
        return _finding(
            "lexical-density",
            "not_applicable",
            title,
            "Se necesitan al menos 50 palabras.",
            metric=f"{len(words)} palabras.",
        )
    percentage = len(content_tokens) / len(words) * 100
    return _finding(
        "lexical-density",
        "informative",
        title,
        "El valor depende del género, la edad, el estilo y el propósito editorial.",
        metric=(
            f"{len(content_tokens)} tokens de contenido de {len(words)} palabras "
            f"({percentage:.1f} %)."
        ),
    )


def _mattr(lemmas: tuple[str, ...], window: int = MATTR_WINDOW) -> float:
    scores = (
        len(set(lemmas[start : start + window])) / window
        for start in range(len(lemmas) - window + 1)
    )
    values = tuple(scores)
    return sum(values) / len(values)


def _lexical_diversity(
    content_tokens: tuple[NlpToken, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[6][1]
    if len(content_tokens) < MATTR_WINDOW:
        return _finding(
            "lexical-diversity",
            "not_applicable",
            title,
            f"Se necesitan al menos {MATTR_WINDOW} tokens de contenido.",
            metric=f"{len(content_tokens)} tokens de contenido.",
        )
    lemmas = tuple(token.normalized_lemma for token in content_tokens)
    value = _mattr(lemmas)
    return _finding(
        "lexical-diversity",
        "informative",
        title,
        (
            "MATTR describe la variación local de lemas sin recomendar "
            "sinónimos automáticos."
        ),
        metric=(
            f"{len(content_tokens)} tokens de contenido · ventana "
            f"{MATTR_WINDOW} · MATTR {value:.3f}."
        ),
    )


def _flesch_szigriszt(words: int, sentences: int, syllables: int) -> float:
    return 206.835 - 62.3 * (syllables / words) - (words / sentences)


def _inflesz_band(value: float) -> str:
    if value < 40:
        return "Muy difícil"
    if value < 55:
        return "Algo difícil"
    if value < 65:
        return "Normal"
    if value < 80:
        return "Bastante fácil"
    return "Muy fácil"


def _syllable_count(words: tuple[NlpToken, ...]) -> int:
    hyphenator = _load_hyphenator()
    return sum(max(1, len(hyphenator.positions(token.text)) + 1) for token in words)


def _flesch_finding(
    words: tuple[NlpToken, ...],
    sentences: tuple[_SentenceRecord, ...],
) -> AdvancedReadabilityFinding:
    title = FINDING_DEFINITIONS[7][1]
    if len(words) < 100 or len(sentences) < 3:
        return _finding(
            "flesch-szigriszt",
            "not_applicable",
            title,
            "El índice requiere al menos 100 palabras y tres oraciones.",
            metric=f"{len(words)} palabras · {len(sentences)} oraciones.",
        )
    try:
        syllables = _syllable_count(words)
    except HyphenationUnavailableError:
        return _finding(
            "flesch-szigriszt",
            "unavailable",
            title,
            "La silabación con el diccionario es_ES no estuvo disponible.",
        )
    except Exception as error:
        logger.error(
            "SEO syllabification failed (dictionary=%s, error=%s).",
            HYPHENATION_DICTIONARY,
            type(error).__name__,
        )
        return _finding(
            "flesch-szigriszt",
            "unavailable",
            title,
            "La silabación con el diccionario es_ES no estuvo disponible.",
        )

    value = _flesch_szigriszt(len(words), len(sentences), syllables)
    band = _inflesz_band(value)
    return _finding(
        "flesch-szigriszt",
        "improve" if value < 55 else "good",
        title,
        (
            "Es un índice orientativo de esta métrica y no una puntuación "
            "general del artículo ni del SEO."
        ),
        metric=(
            f"{len(words)} palabras · {len(sentences)} oraciones · "
            f"{syllables} sílabas · IFSZ {value:.1f} · {band}."
        ),
        value=value,
    )


def analyze_advanced_readability(
    analyzed_segments: tuple[tuple[ContentSegment, AnalyzedText], ...],
) -> tuple[AdvancedReadabilityFinding, ...]:
    sentences = _sentence_records(analyzed_segments)
    words = tuple(token for sentence in sentences for token in sentence.words)
    content_tokens = tuple(
        token for sentence in sentences for token in sentence.content_tokens
    )
    return (
        _long_sentences(sentences),
        _consecutive_openings(sentences),
        _connectors(sentences),
        _periphrastic_passive(sentences),
        _syntactic_complexity(sentences),
        _lexical_density(words, content_tokens),
        _lexical_diversity(content_tokens),
        _flesch_finding(words, sentences),
    )
