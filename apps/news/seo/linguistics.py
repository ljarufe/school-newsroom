from dataclasses import dataclass

from django.conf import settings

from .content import ContentSegment, normalize_whitespace
from .keyphrases import contains_exact_phrase
from .nlp import (
    AnalyzedText,
    NlpInferenceError,
    NlpUnavailableError,
    analyze_texts,
)

INTRODUCTION_TOKEN_LIMIT = 100
DISTRIBUTION_WORD_THRESHOLD = 300
MAX_EVIDENCE_ITEMS = 3
EVIDENCE_CONTEXT_CHARACTERS = 55

STATUS_LABELS = {
    "good": "Correcto",
    "improve": "Por mejorar",
    "informative": "Informativo",
    "not_applicable": "No aplica",
    "unavailable": "No disponible",
}

MODEL_UNAVAILABLE_WARNING = (
    "El análisis lingüístico avanzado no está disponible. Revisa la configuración "
    "del servidor."
)
TEXT_TOO_LONG_WARNING = (
    "El texto es demasiado extenso para el análisis lingüístico configurado."
)


@dataclass(frozen=True)
class LinguisticEvidence:
    text: str
    location: str


@dataclass(frozen=True)
class LinguisticFinding:
    id: str
    group: str
    phrase: str
    status: str
    title: str
    explanation: str
    match_type: str
    evidence: tuple[LinguisticEvidence, ...] = ()
    locations: tuple[str, ...] = ()
    metric: str = ""

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]


@dataclass(frozen=True)
class RelatedKeyphraseAnalysis:
    phrase: str
    findings: tuple[LinguisticFinding, ...]


@dataclass(frozen=True)
class LinguisticAnalysis:
    primary_findings: tuple[LinguisticFinding, ...]
    related_groups: tuple[RelatedKeyphraseAnalysis, ...]
    warning: str = ""


@dataclass(frozen=True)
class _AnalyzedSegment:
    segment: ContentSegment
    analyzed: AnalyzedText
    body_token_offset: int | None


@dataclass(frozen=True)
class _Occurrence:
    match_type: str
    evidence: LinguisticEvidence
    location: str
    body_position: int | None


def _unavailable_finding(
    *, finding_id: str, group: str, phrase: str, title: str
) -> LinguisticFinding:
    return LinguisticFinding(
        id=finding_id,
        group=group,
        phrase=phrase,
        status="unavailable",
        title=title,
        explanation="El análisis lingüístico no estuvo disponible para esta respuesta.",
        match_type="unavailable",
    )


def _not_applicable_primary() -> tuple[LinguisticFinding, ...]:
    return tuple(
        LinguisticFinding(
            id=f"primary-{identifier}",
            group="primary",
            phrase="",
            status="not_applicable",
            title=title,
            explanation=(
                "Añade una frase clave principal para activar esta comprobación."
            ),
            match_type="none",
        )
        for identifier, title in (
            ("variants", "Variantes flexivas"),
            ("introduction", "Introducción"),
            ("distribution", "Distribución de la frase"),
        )
    )


def _unavailable_analysis(
    primary: str,
    related: tuple[str, ...],
    warning: str,
) -> LinguisticAnalysis:
    primary_findings = (
        tuple(
            _unavailable_finding(
                finding_id=f"primary-{identifier}",
                group="primary",
                phrase=primary,
                title=title,
            )
            for identifier, title in (
                ("variants", "Variantes flexivas"),
                ("introduction", "Introducción"),
                ("distribution", "Distribución de la frase"),
            )
        )
        if primary
        else _not_applicable_primary()
    )
    related_groups = tuple(
        RelatedKeyphraseAnalysis(
            phrase=phrase,
            findings=tuple(
                _unavailable_finding(
                    finding_id=f"related-{index}-{identifier}",
                    group=f"related-{index}",
                    phrase=phrase,
                    title=title,
                )
                for identifier, title in (
                    ("presence", "Presencia"),
                    ("locations", "Ubicaciones"),
                    ("distribution", "Distribución de la frase"),
                )
            ),
        )
        for index, phrase in enumerate(related)
    )
    return LinguisticAnalysis(primary_findings, related_groups, warning)


def _body_offset(segment: ContentSegment, current_offset: int) -> int | None:
    return current_offset if segment.reference.startswith("body:") else None


def _prepare_segments(
    segments: tuple[ContentSegment, ...],
    analyzed_texts: tuple[AnalyzedText, ...],
) -> tuple[tuple[_AnalyzedSegment, ...], int]:
    prepared = []
    body_token_count = 0
    for segment, analyzed in zip(segments, analyzed_texts, strict=True):
        offset = _body_offset(segment, body_token_count)
        prepared.append(_AnalyzedSegment(segment, analyzed, offset))
        if offset is not None:
            body_token_count += sum(token.significant for token in analyzed.tokens)
    return tuple(prepared), body_token_count


def _location_for(
    segment: ContentSegment,
    body_position: int | None,
) -> str:
    if segment.kind in {"public_title", "seo_title"}:
        return "Título público o SEO"
    if segment.kind == "description":
        return "Descripción"
    if segment.kind == "heading":
        return "Subtítulos"
    if body_position is not None and body_position < INTRODUCTION_TOKEN_LIMIT:
        return "Introducción"
    return "Cuerpo"


def _evidence_text(text: str, start: int, end: int) -> str:
    left = max(0, start - EVIDENCE_CONTEXT_CHARACTERS)
    right = min(len(text), end + EVIDENCE_CONTEXT_CHARACTERS)
    snippet = normalize_whitespace(text[left:right])
    if left:
        snippet = f"…{snippet}"
    if right < len(text):
        snippet = f"{snippet}…"
    return snippet


def _find_occurrences(
    phrase_doc: AnalyzedText,
    prepared_segments: tuple[_AnalyzedSegment, ...],
) -> tuple[_Occurrence, ...]:
    phrase_tokens = tuple(token for token in phrase_doc.tokens if token.significant)
    if not phrase_tokens:
        return ()
    phrase_surfaces = tuple(token.normalized_text for token in phrase_tokens)
    phrase_lemmas = tuple(token.normalized_lemma for token in phrase_tokens)
    permits_flexive = any(token.content for token in phrase_tokens)
    occurrences = []

    for prepared in prepared_segments:
        significant = tuple(
            token for token in prepared.analyzed.tokens if token.significant
        )
        significant_positions = {
            id(token): index for index, token in enumerate(significant)
        }
        width = len(phrase_tokens)
        for start_index in range(max(0, len(significant) - width + 1)):
            candidate = significant[start_index : start_index + width]
            candidate_surfaces = tuple(token.normalized_text for token in candidate)
            candidate_lemmas = tuple(token.normalized_lemma for token in candidate)
            lemma_match = permits_flexive and candidate_lemmas == phrase_lemmas
            if candidate_surfaces != phrase_surfaces and not lemma_match:
                continue

            start = candidate[0].start
            end = candidate[-1].end
            candidate_text = prepared.analyzed.text[start:end]
            if contains_exact_phrase(candidate_text, phrase_doc.text):
                match_type = "exact"
            elif lemma_match:
                match_type = "flexive"
            else:
                continue

            body_position = None
            if prepared.body_token_offset is not None:
                body_position = (
                    prepared.body_token_offset + significant_positions[id(candidate[0])]
                )
            location = _location_for(prepared.segment, body_position)
            occurrences.append(
                _Occurrence(
                    match_type=match_type,
                    evidence=LinguisticEvidence(
                        text=_evidence_text(prepared.analyzed.text, start, end),
                        location=location,
                    ),
                    location=location,
                    body_position=body_position,
                )
            )
    return tuple(occurrences)


def _match_type(occurrences: tuple[_Occurrence, ...]) -> str:
    types = {occurrence.match_type for occurrence in occurrences}
    if types == {"exact", "flexive"}:
        return "exact_and_flexive"
    if "exact" in types:
        return "exact"
    if "flexive" in types:
        return "flexive"
    return "none"


def _evidence(occurrences: tuple[_Occurrence, ...]) -> tuple[LinguisticEvidence, ...]:
    return tuple(occurrence.evidence for occurrence in occurrences[:MAX_EVIDENCE_ITEMS])


def _locations(occurrences: tuple[_Occurrence, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(occurrence.location for occurrence in occurrences))


def _presence_finding(
    *,
    finding_id: str,
    group: str,
    phrase: str,
    title: str,
    occurrences: tuple[_Occurrence, ...],
) -> LinguisticFinding:
    exact_count = sum(item.match_type == "exact" for item in occurrences)
    flexive_count = sum(item.match_type == "flexive" for item in occurrences)
    if occurrences:
        found_verb = "Se encontró" if len(occurrences) == 1 else "Se encontraron"
        exact_noun = (
            "coincidencia exacta" if exact_count == 1 else "coincidencias exactas"
        )
        flexive_noun = (
            "variante flexiva adicional"
            if flexive_count == 1
            else "variantes flexivas adicionales"
        )
        explanation = (
            f"{found_verb} {exact_count} {exact_noun} y {flexive_count} {flexive_noun}."
        )
        status = "good"
    else:
        explanation = "No se encontró una coincidencia exacta ni una variante flexiva."
        status = "improve"
    return LinguisticFinding(
        id=finding_id,
        group=group,
        phrase=phrase,
        status=status,
        title=title,
        explanation=explanation,
        match_type=_match_type(occurrences),
        evidence=_evidence(occurrences),
        locations=_locations(occurrences),
        metric=f"exact={exact_count}; flexive={flexive_count}",
    )


def _introduction_finding(
    phrase: str,
    occurrences: tuple[_Occurrence, ...],
) -> LinguisticFinding:
    introduction = tuple(
        item
        for item in occurrences
        if item.body_position is not None
        and item.body_position < INTRODUCTION_TOKEN_LIMIT
    )
    match_type = _match_type(introduction)
    if match_type in {"exact", "exact_and_flexive"}:
        status = "good"
        explanation = "La introducción contiene una coincidencia exacta."
    elif match_type == "flexive":
        status = "good"
        explanation = "La introducción contiene sólo una variante flexiva."
    else:
        status = "improve"
        explanation = "La frase no aparece en los primeros 100 tokens significativos."
    return LinguisticFinding(
        id="primary-introduction",
        group="primary",
        phrase=phrase,
        status=status,
        title="Introducción",
        explanation=explanation,
        match_type=match_type,
        evidence=_evidence(introduction),
        locations=_locations(introduction),
        metric=f"token_limit={INTRODUCTION_TOKEN_LIMIT}",
    )


def _distribution_finding(
    *,
    finding_id: str,
    group: str,
    phrase: str,
    occurrences: tuple[_Occurrence, ...],
    body_token_count: int,
) -> LinguisticFinding:
    body_occurrences = tuple(
        item for item in occurrences if item.body_position is not None
    )
    if body_token_count < DISTRIBUTION_WORD_THRESHOLD:
        status = "not_applicable"
        explanation = (
            "La distribución se aplica a contenidos de 300 palabras significativas "
            "o más."
        )
        zones: set[int] = set()
    else:
        zones = {
            min(2, item.body_position * 3 // body_token_count)
            for item in body_occurrences
        }
        if len(body_occurrences) >= 2 and len(zones) >= 2:
            status = "good"
            explanation = "La frase aparece al menos dos veces en dos o más zonas."
        elif len(body_occurrences) >= 2:
            status = "improve"
            explanation = "Las ocurrencias están concentradas en una sola zona."
        elif len(body_occurrences) == 1:
            status = "informative"
            explanation = "La frase aparece una vez en el cuerpo."
        else:
            status = "improve"
            explanation = "La frase no aparece en el cuerpo."
    return LinguisticFinding(
        id=finding_id,
        group=group,
        phrase=phrase,
        status=status,
        title="Distribución de la frase",
        explanation=explanation,
        match_type=_match_type(body_occurrences),
        evidence=_evidence(body_occurrences),
        locations=_locations(body_occurrences),
        metric=(
            f"body_tokens={body_token_count}; occurrences={len(body_occurrences)}; "
            f"zones={','.join(str(zone + 1) for zone in sorted(zones)) or 'none'}"
        ),
    )


def _locations_finding(
    *,
    group: str,
    group_index: int,
    phrase: str,
    occurrences: tuple[_Occurrence, ...],
) -> LinguisticFinding:
    locations = _locations(occurrences)
    return LinguisticFinding(
        id=f"related-{group_index}-locations",
        group=group,
        phrase=phrase,
        status="good" if locations else "improve",
        title="Ubicaciones",
        explanation=(
            f"Se encontró en: {', '.join(locations)}."
            if locations
            else "No se encontraron ubicaciones para esta frase."
        ),
        match_type=_match_type(occurrences),
        evidence=_evidence(occurrences),
        locations=locations,
        metric=f"locations={len(locations)}",
    )


def analyze_linguistic_keyphrases(
    segments: tuple[ContentSegment, ...],
    primary_phrase: str,
    related_phrases: tuple[str, ...],
) -> LinguisticAnalysis:
    primary = normalize_whitespace(primary_phrase)
    related = tuple(
        normalized
        for phrase in related_phrases
        if (normalized := normalize_whitespace(phrase))
    )
    phrases = ((primary,) if primary else ()) + related
    if not phrases:
        return LinguisticAnalysis(_not_applicable_primary(), ())
    if sum(len(segment.text) for segment in segments) > settings.SEO_NLP_MAX_CHARACTERS:
        return _unavailable_analysis(primary, related, TEXT_TOO_LONG_WARNING)

    try:
        analyzed = analyze_texts((*phrases, *(segment.text for segment in segments)))
    except (NlpUnavailableError, NlpInferenceError):
        return _unavailable_analysis(primary, related, MODEL_UNAVAILABLE_WARNING)

    phrase_docs = analyzed[: len(phrases)]
    prepared, body_token_count = _prepare_segments(
        segments,
        analyzed[len(phrases) :],
    )
    phrase_occurrences = tuple(
        _find_occurrences(phrase_doc, prepared) for phrase_doc in phrase_docs
    )

    phrase_index = 0
    if primary:
        primary_occurrences = phrase_occurrences[0]
        primary_findings = (
            _presence_finding(
                finding_id="primary-variants",
                group="primary",
                phrase=primary,
                title="Variantes flexivas",
                occurrences=primary_occurrences,
            ),
            _introduction_finding(primary, primary_occurrences),
            _distribution_finding(
                finding_id="primary-distribution",
                group="primary",
                phrase=primary,
                occurrences=primary_occurrences,
                body_token_count=body_token_count,
            ),
        )
        phrase_index = 1
    else:
        primary_findings = _not_applicable_primary()

    related_groups = []
    for index, phrase in enumerate(related):
        occurrences = phrase_occurrences[phrase_index + index]
        group = f"related-{index}"
        related_groups.append(
            RelatedKeyphraseAnalysis(
                phrase=phrase,
                findings=(
                    _presence_finding(
                        finding_id=f"related-{index}-presence",
                        group=group,
                        phrase=phrase,
                        title="Presencia",
                        occurrences=occurrences,
                    ),
                    _locations_finding(
                        group=group,
                        group_index=index,
                        phrase=phrase,
                        occurrences=occurrences,
                    ),
                    _distribution_finding(
                        finding_id=f"related-{index}-distribution",
                        group=group,
                        phrase=phrase,
                        occurrences=occurrences,
                        body_token_count=body_token_count,
                    ),
                ),
            )
        )
    return LinguisticAnalysis(primary_findings, tuple(related_groups))
