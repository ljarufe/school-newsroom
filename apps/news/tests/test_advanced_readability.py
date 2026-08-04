import importlib.metadata
from types import SimpleNamespace

import pytest

from apps.news.seo import advanced_readability as advanced
from apps.news.seo import analyze_page
from apps.news.seo.advanced_readability import CONNECTOR_LEXICON
from apps.news.seo.analysis import AnalysisResult
from apps.news.seo.linguistics import analyze_linguistic_keyphrases
from apps.news.seo.nlp import NlpInferenceError, analyze_texts
from apps.news.tests.test_seo import make_page


def finding_by_title(result, title):
    return next(
        finding
        for finding in result.advanced_readability_checks
        if finding.title == title
    )


def sentence_with_words(count: int, word: str = "palabra") -> str:
    return f"{' '.join([word] * count)}."


def paragraph_with_sentences(sentences: list[str]) -> list[tuple[str, str]]:
    return [("paragraph", f"<p>{' '.join(sentences)}</p>")]


def simple_sentences(count: int) -> list[str]:
    return [
        f"El equipo revisa la nota ficticia número {index}." for index in range(count)
    ]


@pytest.mark.parametrize(
    ("word_count", "expected_status", "expected_long_count"),
    [(30, "good", 0), (31, "improve", 1)],
)
def test_long_sentence_uses_strict_more_than_30_boundary(
    word_count,
    expected_status,
    expected_long_count,
) -> None:
    result = analyze_page(
        make_page(body=paragraph_with_sentences([sentence_with_words(word_count)]))
    )

    finding = finding_by_title(result, "Oraciones extensas con evidencia")
    assert finding.status == expected_status
    assert finding.metric.startswith(f"{expected_long_count} de 1")


@pytest.mark.parametrize(
    ("sentences", "expected_status", "expected_percentage"),
    [
        ([sentence_with_words(31), *simple_sentences(3)], "good", "25 %"),
        ([sentence_with_words(31), *simple_sentences(2)], "improve", "33 %"),
    ],
)
def test_long_sentence_ratio_uses_strict_more_than_25_percent(
    sentences,
    expected_status,
    expected_percentage,
) -> None:
    result = analyze_page(make_page(body=paragraph_with_sentences(sentences)))

    finding = finding_by_title(result, "Oraciones extensas con evidencia")
    assert finding.status == expected_status
    assert expected_percentage in finding.metric


def test_long_sentence_evidence_is_prioritized_bounded_and_located() -> None:
    body = [
        ("paragraph", f"<p>{sentence_with_words(length)}</p>")
        for length in (31, 34, 33, 32)
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=body)),
        "Oraciones extensas con evidencia",
    )

    assert len(finding.evidence) == 3
    assert [item.metric for item in finding.evidence] == [
        "34 palabras",
        "33 palabras",
        "32 palabras",
    ]
    assert finding.evidence[0].location == "Párrafo 2 (body:1:0)"
    assert all(
        len(item.text) <= advanced.MAX_EVIDENCE_CHARACTERS for item in finding.evidence
    )


@pytest.mark.parametrize(
    ("sentences", "expected_status"),
    [
        (
            [
                "El equipo escolar revisa notas.",
                "Los equipos escolares comparan datos.",
                "La editora escolar publica el informe.",
            ],
            "good",
        ),
        (
            [
                "El equipo escolar revisa notas.",
                "Los equipos escolares comparan datos.",
                "El equipo escolar publica el informe.",
            ],
            "improve",
        ),
    ],
)
def test_consecutive_openings_require_three_lemmatized_signatures(
    sentences,
    expected_status,
) -> None:
    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Comienzos consecutivos",
    )

    assert finding.status == expected_status
    if expected_status == "improve":
        assert finding.metric == "1 secuencia problemática."
        assert "equipo escolar" in finding.evidence[0].metric
        assert "3 oraciones consecutivas" in finding.evidence[0].metric


def test_heading_breaks_a_consecutive_opening_run() -> None:
    body = [
        (
            "paragraph",
            "<p>El equipo escolar revisa notas.</p>"
            "<p>El equipo escolar contrasta fuentes.</p>"
            "<h2>Una nueva sección</h2>"
            "<p>El equipo escolar publica el informe.</p>",
        )
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=body)),
        "Comienzos consecutivos",
    )

    assert finding.status == "good"
    assert finding.evidence == ()


def test_consecutive_authorized_segments_share_an_opening_run() -> None:
    body = [
        (
            "paragraph",
            "<p>El equipo escolar revisa notas.</p>"
            "<ul><li>El equipo escolar contrasta fuentes.</li></ul>"
            "<blockquote>El equipo escolar publica el informe.</blockquote>",
        )
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=body)),
        "Comienzos consecutivos",
    )

    assert finding.status == "improve"
    assert finding.metric == "1 secuencia problemática."
    assert "3 oraciones consecutivas" in finding.evidence[0].metric


@pytest.mark.parametrize(
    ("connector_sentences", "expected_status", "expected_metric"),
    [
        ([], "improve", "0 de 10"),
        (["Además, el equipo revisa la nota ficticia."], "informative", "1 de 10"),
        (
            [
                "Además, el equipo revisa la nota ficticia.",
                "Sin embargo, la editora contrasta los datos.",
            ],
            "good",
            "2 de 10",
        ),
    ],
)
def test_connector_ratio_covers_zero_ten_and_twenty_percent(
    connector_sentences,
    expected_status,
    expected_metric,
) -> None:
    sentences = [*connector_sentences, *simple_sentences(10 - len(connector_sentences))]
    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Uso de conectores",
    )

    assert finding.status == expected_status
    assert expected_metric in finding.metric


def test_multiword_connectors_are_matched_first_and_sentence_counts_once() -> None:
    sentences = [
        "Por otra parte, el equipo compara datos; sin embargo, mantiene dudas.",
        *simple_sentences(9),
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Uso de conectores",
    )

    assert "1 de 10" in finding.metric
    assert len(finding.evidence) == 1
    assert "por otra parte" in finding.evidence[0].metric
    assert "sin embargo" in finding.evidence[0].metric
    assert "Adición" in finding.metric
    assert "Contraste o concesión" in finding.metric


def test_connector_lexicon_is_the_approved_versioned_list() -> None:
    assert CONNECTOR_LEXICON == (
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


def test_passive_accepts_ser_participle_and_rejects_estar_and_reflexive_se() -> None:
    sentences = [
        "El borrador fue revisado por dos editoras.",
        "El segundo borrador está revisado por dos editoras.",
        "El tercer borrador se revisó ayer.",
        *simple_sentences(7),
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Pasiva perifrástica",
    )

    assert finding.status == "informative"
    assert "1 de 10" in finding.metric
    assert len(finding.evidence) == 1
    assert "fue revisado" in finding.evidence[0].text


def test_two_passives_at_ten_percent_need_improvement() -> None:
    sentences = [
        "El borrador fue revisado por dos editoras.",
        "La conclusión fue publicada por el equipo.",
        *simple_sentences(18),
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Pasiva perifrástica",
    )

    assert finding.status == "improve"
    assert "2 de 20" in finding.metric


def test_syntactic_complexity_requires_three_clause_heads() -> None:
    two_heads = "La editora explicó que el texto mejoraría."
    three_heads = (
        "La editora explicó que el texto mejoraría cuando el equipo separara las ideas."
    )

    simple_result = analyze_page(
        make_page(body=paragraph_with_sentences([two_heads, *simple_sentences(2)]))
    )
    complex_result = analyze_page(
        make_page(body=paragraph_with_sentences([three_heads, *simple_sentences(2)]))
    )

    simple_finding = finding_by_title(simple_result, "Complejidad sintáctica")
    complex_finding = finding_by_title(complex_result, "Complejidad sintáctica")
    assert simple_finding.status == "good"
    assert complex_finding.status == "improve"
    assert complex_finding.evidence[0].metric == "3 cabezas de cláusula estimadas"


def test_nominal_conjunction_does_not_add_a_clause_head() -> None:
    sentences = [
        "La editora revisó el texto y las fuentes.",
        *simple_sentences(2),
    ]

    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Complejidad sintáctica",
    )

    assert finding.status == "good"
    assert not finding.evidence


@pytest.mark.parametrize(
    ("word_count", "expected_status"),
    [(49, "not_applicable"), (50, "informative")],
)
def test_lexical_density_gate_is_50_words(word_count, expected_status) -> None:
    finding = finding_by_title(
        analyze_page(
            make_page(
                body=paragraph_with_sentences(
                    [sentence_with_words(word_count, "contenido")]
                )
            )
        ),
        "Densidad léxica",
    )

    assert finding.status == expected_status
    assert f"{word_count} palabras" in finding.metric


@pytest.mark.parametrize(
    ("content_count", "expected_status"),
    [(49, "not_applicable"), (50, "informative"), (51, "informative")],
)
def test_mattr_gate_and_window_boundaries(content_count, expected_status) -> None:
    finding = finding_by_title(
        analyze_page(
            make_page(
                body=paragraph_with_sentences(
                    [sentence_with_words(content_count, "contenido")]
                )
            )
        ),
        "Diversidad léxica",
    )

    assert finding.status == expected_status
    assert f"{content_count} tokens de contenido" in finding.metric
    if expected_status == "informative":
        assert "ventana 50" in finding.metric
        assert "MATTR 0.020" in finding.metric


def test_mattr_averages_all_consecutive_windows() -> None:
    lemmas = tuple(["repetido"] * 50 + ["nuevo"])

    assert advanced._mattr(lemmas) == pytest.approx((0.02 + 0.04) / 2)


def test_flesch_szigriszt_formula_preserves_unrounded_value() -> None:
    value = advanced._flesch_szigriszt(words=120, sentences=6, syllables=240)

    assert value == pytest.approx(62.235)


def test_real_pyphen_uses_bundled_es_dictionary_and_single_initialization() -> None:
    pyphen_module = advanced.importlib.import_module("pyphen")
    advanced.reset_hyphenation_cache()
    try:
        first = advanced._load_hyphenator()
        second = advanced._load_hyphenator()

        assert first is second
        assert importlib.metadata.version("pyphen") == "0.17.2"
        assert pyphen_module.language_fallback("es_ES") == "es"
        assert pyphen_module.LANGUAGES["es"].is_file()
        assert first.inserted("extraordinario") == "ex-tra-or-di-na-rio"
        assert advanced.hyphenation_load_attempts() == 1
    finally:
        advanced.reset_hyphenation_cache()


@pytest.mark.parametrize(
    ("value", "band"),
    [
        (39.999, "Muy difícil"),
        (40, "Algo difícil"),
        (55, "Normal"),
        (65, "Bastante fácil"),
        (80, "Muy fácil"),
    ],
)
def test_inflesz_band_boundaries(value, band) -> None:
    assert advanced._inflesz_band(value) == band


@pytest.mark.parametrize(
    ("counts", "expected_status"),
    [
        ((33, 33, 33), "not_applicable"),
        ((34, 33, 33), "good"),
        ((50, 50), "not_applicable"),
    ],
)
def test_flesch_reliability_gate_is_100_words_and_three_sentences(
    monkeypatch,
    counts,
    expected_status,
) -> None:
    monkeypatch.setattr(
        advanced,
        "_syllable_count",
        lambda words: len(words),
    )
    sentences = [sentence_with_words(count) for count in counts]

    finding = finding_by_title(
        analyze_page(make_page(body=paragraph_with_sentences(sentences))),
        "Flesch-Szigriszt e INFLESZ",
    )

    assert finding.status == expected_status
    assert f"{sum(counts)} palabras" in finding.metric
    if expected_status != "not_applicable":
        assert "IFSZ 111.2" in finding.metric
        assert "Muy fácil" in finding.metric
        assert finding.value == pytest.approx(
            advanced._flesch_szigriszt(sum(counts), len(counts), sum(counts))
        )


def test_only_authorized_body_prose_enters_advanced_denominators() -> None:
    long_sentence = sentence_with_words(31)
    page = make_page(
        title="Título excluido " + long_sentence,
        seo_title="Título SEO excluido " + long_sentence,
        search_description="Descripción excluida " + long_sentence,
        body=[
            (
                "paragraph",
                f"<h2>Subtítulo excluido {long_sentence}</h2>"
                f"<p>{long_sentence}</p>"
                f"<ul><li>{long_sentence}</li></ul>"
                f"<blockquote>{long_sentence}</blockquote>",
            ),
            (
                "table",
                {
                    "data": [["Tabla excluida " + long_sentence]],
                    "first_row_is_table_header": False,
                    "first_col_is_header": False,
                    "table_caption": "Tabla ficticia",
                },
            ),
            (
                "article_image",
                {
                    "image": None,
                    "caption": "Pie excluido",
                    "alt_text": "Alt excluido " + long_sentence,
                    "credit": "Crédito excluido",
                },
            ),
        ],
    )

    finding = finding_by_title(
        analyze_page(page),
        "Oraciones extensas con evidencia",
    )

    assert finding.metric.startswith("3 de 3")
    assert [item.location for item in finding.evidence] == [
        "Párrafo 1 (body:0:1)",
        "Lista 1 (body:0:2)",
        "Cita 1 (body:0:3)",
    ]
    assert all("excluido" not in item.text.casefold() for item in finding.evidence)


def test_sentences_never_cross_editorial_segments() -> None:
    result = analyze_page(
        make_page(
            body=[
                ("paragraph", "<p>Primer fragmento sin punto final</p>"),
                ("paragraph", "<p>Segundo fragmento con cierre.</p>"),
            ]
        )
    )

    finding = finding_by_title(result, "Oraciones extensas con evidencia")
    assert finding.metric.startswith("0 de 2")


def test_single_spacy_inference_batch_is_reused_for_all_findings(monkeypatch) -> None:
    from apps.news.seo import linguistics

    original = linguistics.analyze_texts
    calls = []

    def counted(values):
        calls.append(tuple(values))
        return original(calls[-1])

    monkeypatch.setattr(linguistics, "analyze_texts", counted)

    result = analyze_page(make_page())

    assert len(calls) == 1
    assert len(result.advanced_readability_checks) == 8


def test_advanced_findings_never_change_the_overall_status() -> None:
    paragraphs = []
    for index in range(6):
        if index == 0:
            sentences = [
                "El equipo escolar revisa contenido claro para la comunidad local "
                "cada jornada ficticia.",
                "El equipo escolar compara contenido claro para la comunidad local "
                "cada jornada ficticia.",
                "El equipo escolar publica contenido claro para la comunidad local "
                "cada jornada ficticia.",
                "La redacción presenta contenido claro para la comunidad local cada "
                "jornada ficticia.",
            ]
            prefix = "El periodismo escolar orienta el trabajo. "
        else:
            sentences = [
                "La redacción presenta contenido claro para la comunidad local cada "
                "jornada ficticia."
            ] * 4
            prefix = ""
        paragraphs.append(f"<p>{prefix}{' '.join(sentences)}</p>")
    body = (
        "<h2>Periodismo escolar en contexto</h2>"
        + "".join(paragraphs[:3])
        + "<h2>Trabajo de la comunidad</h2>"
        + "".join(paragraphs[3:])
        + '<p><a linktype="page" id="2">Noticia relacionada</a> '
        + '<a href="https://example.org/source">Fuente externa</a>.</p>'
    )
    page = make_page(
        seo_title="Periodismo escolar: guía para una redacción local",
        search_description=(
            "El periodismo escolar fortalece la investigación y la escritura "
            "con prácticas claras para publicar noticias locales responsables."
        ),
        body=[("paragraph", body)],
    )

    result = analyze_page(page, site_hostname="school.test")

    assert result.overall_label == "Bueno"
    assert finding_by_title(result, "Comienzos consecutivos").status == "improve"


def test_analysis_result_preserves_the_existing_positional_constructor() -> None:
    result = AnalysisResult((), (), (), (), "", "good", "Bueno")

    assert result.advanced_readability_checks == ()


def test_inference_failure_preserves_basic_analysis_and_marks_advanced_unavailable(
    monkeypatch,
) -> None:
    from apps.news.seo import linguistics

    monkeypatch.setattr(
        linguistics,
        "analyze_texts",
        lambda values: (_ for _ in ()).throw(NlpInferenceError()),
    )

    result = analyze_page(make_page())

    assert result.seo_checks
    assert result.readability_checks
    assert len(result.advanced_readability_checks) == 8
    assert all(
        finding.status == "unavailable"
        for finding in result.advanced_readability_checks
    )


def test_pyphen_failure_only_marks_flesch_unavailable_and_is_cached(
    monkeypatch,
    caplog,
) -> None:
    sensitive_text = "contenido editorial sensible que no debe registrarse"
    body_text = " ".join([sensitive_text] * 20)
    page = make_page(
        body=paragraph_with_sentences(
            [f"{body_text}.", f"{body_text}.", f"{body_text}."]
        )
    )
    advanced.reset_hyphenation_cache()

    def fail_import(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(advanced.importlib, "import_module", fail_import)
    try:
        first = analyze_page(page)
        second = analyze_page(page)
    finally:
        advanced.reset_hyphenation_cache()

    assert all(
        finding.status != "unavailable"
        for finding in first.advanced_readability_checks[:7]
    )
    assert first.advanced_readability_checks[-1].status == "unavailable"
    assert second.advanced_readability_checks[-1].status == "unavailable"
    assert (
        sum(
            "syllabification initialization failed" in record.message
            for record in caplog.records
        )
        == 1
    )
    assert sensitive_text not in caplog.text


def test_public_linguistic_result_keeps_stable_advanced_order() -> None:
    segments = ()
    result = analyze_linguistic_keyphrases(segments, "", ())

    assert [finding.title for finding in result.advanced_readability_checks] == [
        title for _finding_id, title in advanced.FINDING_DEFINITIONS
    ]


def test_common_word_definition_excludes_digits_and_punctuation() -> None:
    analyzed = analyze_texts(("Texto útil, versión 2026 y aula2.",))[0]
    words = [token.text for token in analyzed.tokens if token.word]

    assert words == ["Texto", "útil", "versión", "y"]


def test_nlp_boundary_exposes_only_project_owned_sentence_and_dependency_data() -> None:
    analyzed = analyze_texts(("El borrador fue revisado por dos editoras.",))[0]
    participle = next(token for token in analyzed.tokens if token.text == "revisado")
    auxiliary = next(token for token in analyzed.tokens if token.text == "fue")

    assert len(analyzed.sentences) == 1
    assert analyzed.sentences[0].token_start == 0
    assert analyzed.sentences[0].token_end == len(analyzed.tokens)
    assert participle.dependency == "ROOT"
    assert participle.head_index == participle.index
    assert "VerbForm=Part" in participle.morphology
    assert participle.sentence_index == 0
    assert auxiliary.dependency == "aux"
    assert auxiliary.head_index == participle.index
    assert auxiliary.normalized_lemma == "ser"


def test_advanced_findings_are_immutable_project_structures() -> None:
    finding = analyze_page(make_page()).advanced_readability_checks[0]

    with pytest.raises(AttributeError):
        finding.status = "improve"
    assert not isinstance(finding, SimpleNamespace)
