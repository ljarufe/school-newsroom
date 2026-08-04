from types import SimpleNamespace

import pytest
from django.test import override_settings

from apps.news.seo import analyze_page, extract_content
from apps.news.seo.linguistics import (
    MODEL_UNAVAILABLE_WARNING,
    TEXT_TOO_LONG_WARNING,
)
from apps.news.seo.nlp import reset_runtime_cache, runtime_info
from apps.news.tests.test_seo import make_page


def finding_by_title(findings, title):
    return next(finding for finding in findings if finding.title == title)


def with_related(page, *phrases):
    page.related_keyphrases = [SimpleNamespace(phrase=phrase) for phrase in phrases]
    return page


def test_real_pipeline_distinguishes_exact_and_additional_flexive_matches() -> None:
    page = make_page(
        focus_keyphrase="investigación escolar",
        body=[
            (
                "paragraph",
                "<p>La investigación escolar continúa. Las investigaciones "
                "escolares avanzan; la investigación escolar se documenta.</p>",
            )
        ],
    )

    result = analyze_page(page)
    finding = finding_by_title(result.primary_linguistic_checks, "Variantes flexivas")

    assert finding.status == "good"
    assert finding.match_type == "exact_and_flexive"
    assert finding.metric == "exact=2; flexive=1"
    assert len(finding.evidence) == 3
    assert runtime_info().load_attempts == 1
    assert "ner" not in runtime_info().components


@pytest.mark.parametrize(
    ("phrase", "value"),
    [
        ("estudiante comprometido", "La estudiante comprometida escribe."),
        ("estudiante investiga", "Los estudiantes investigaron el caso."),
        (
            "investigación escolar",
            "Las investigaciones, escolares avanzan responsablemente.",
        ),
    ],
)
def test_flexive_matching_handles_bounded_spanish_variation(phrase, value) -> None:
    result = analyze_page(
        make_page(
            title="Noticia ficticia",
            seo_title="Título ficticio",
            search_description="Descripción ficticia.",
            focus_keyphrase=phrase,
            body=[("paragraph", f"<p>{value}</p>")],
        )
    )

    finding = finding_by_title(result.primary_linguistic_checks, "Variantes flexivas")
    assert finding.match_type == "flexive"
    assert finding.metric == "exact=0; flexive=1"


@pytest.mark.parametrize(
    ("phrase", "value"),
    [
        ("investigación escolar", "La escolar investigación continúa."),
        ("investigación escolar", "El estudio educativo continúa."),
        ("estudiante investiga", "La investigación ayuda al estudiante."),
    ],
)
def test_flexive_matching_rejects_reordering_synonyms_and_noncontiguous_words(
    phrase,
    value,
) -> None:
    result = analyze_page(
        make_page(
            title="Noticia ficticia",
            seo_title="Título ficticio",
            search_description="Descripción ficticia.",
            focus_keyphrase=phrase,
            body=[("paragraph", f"<p>{value}</p>")],
        )
    )

    finding = finding_by_title(result.primary_linguistic_checks, "Variantes flexivas")
    assert finding.status == "improve"
    assert finding.match_type == "none"


def test_real_small_model_false_negative_is_kept_conservative() -> None:
    result = analyze_page(
        make_page(
            title="Noticia ficticia",
            seo_title="Título ficticio",
            search_description="Descripción ficticia.",
            focus_keyphrase="reportero joven",
            body=[
                (
                    "paragraph",
                    "<p>Las reporteras jóvenes publicaron la nota.</p>",
                )
            ],
        )
    )

    finding = finding_by_title(result.primary_linguistic_checks, "Variantes flexivas")
    assert finding.match_type == "none"


def test_structured_segments_cover_headings_lists_quotes_tables_and_image_alt() -> None:
    page = with_related(
        make_page(
            title="Crónica local",
            seo_title="Crónica escolar",
            search_description="Descripción con boletín comunitario.",
            body=[
                (
                    "paragraph",
                    "<h2>Jóvenes reporteros</h2>"
                    "<ul><li>Noticia escolar</li></ul>"
                    "<blockquote>Redacción periodística</blockquote>",
                ),
                (
                    "table",
                    {
                        "data": [["investigaciones escolares", "dato ficticio"]],
                        "first_row_is_table_header": False,
                        "first_col_is_header": False,
                        "table_caption": "Hallazgos",
                    },
                ),
                (
                    "article_image",
                    {
                        "image": None,
                        "caption": "Imagen ficticia",
                        "alt_text": "equipo periodístico escolar",
                        "credit": "",
                    },
                ),
            ],
        ),
        "jóvenes reporteros",
        "noticia escolar",
        "redacción periodística",
        "investigación escolar",
    )

    snapshot = extract_content(page.body)
    result = analyze_page(page)

    assert [segment.kind for segment in snapshot.segments] == [
        "heading",
        "list",
        "quote",
        "table",
        "image_alt",
    ]
    assert [group.phrase for group in result.related_keyphrase_groups] == [
        "jóvenes reporteros",
        "noticia escolar",
        "redacción periodística",
        "investigación escolar",
    ]
    assert finding_by_title(
        result.related_keyphrase_groups[0].findings, "Ubicaciones"
    ).locations == ("Subtítulos",)
    assert (
        finding_by_title(
            result.related_keyphrase_groups[3].findings, "Presencia"
        ).match_type
        == "flexive"
    )


def test_primary_introduction_uses_first_100_significant_body_tokens() -> None:
    before = " ".join(["contexto"] * 100)
    page = make_page(
        title="Noticia ficticia",
        seo_title="Título ficticio",
        search_description="Descripción ficticia.",
        focus_keyphrase="periodismo escolar",
        body=[("paragraph", f"<p>{before} periodismo escolar.</p>")],
    )

    result = analyze_page(page)
    introduction = finding_by_title(result.primary_linguistic_checks, "Introducción")

    assert introduction.status == "improve"
    assert introduction.metric == "token_limit=100"


def test_distribution_uses_three_testable_zones_after_300_body_tokens() -> None:
    first = "noticia escolar " + " ".join(["contexto"] * 140)
    middle = " ".join(["contexto"] * 80)
    final = "Las noticias escolares " + " ".join(["contexto"] * 90)
    page = make_page(
        title="Noticia ficticia",
        seo_title="Título ficticio",
        search_description="Descripción ficticia.",
        focus_keyphrase="noticia escolar",
        body=[
            ("paragraph", f"<p>{first}</p>"),
            ("paragraph", f"<p>{middle}</p>"),
            ("paragraph", f"<p>{final}</p>"),
        ],
    )

    distribution = finding_by_title(
        analyze_page(page).primary_linguistic_checks,
        "Distribución de la frase",
    )

    assert distribution.status == "good"
    assert "body_tokens=315" in distribution.metric
    assert "zones=1,3" in distribution.metric


def test_related_and_linguistic_findings_do_not_change_overall_status() -> None:
    page = make_page(body=[("paragraph", "<p>Investigaciones escolares.</p>")])
    baseline = analyze_page(page)
    with_related(page, "investigación escolar")
    extended = analyze_page(page)

    assert (extended.overall_status, extended.overall_label) == (
        baseline.overall_status,
        baseline.overall_label,
    )


@override_settings(SEO_NLP_MAX_CHARACTERS=10)
def test_over_limit_text_is_not_silently_truncated() -> None:
    result = analyze_page(make_page())

    assert result.nlp_warning == TEXT_TOO_LONG_WARNING
    assert all(
        finding.status == "unavailable" for finding in result.primary_linguistic_checks
    )
    assert len(result.advanced_readability_checks) == 8
    assert all(
        finding.status == "unavailable"
        for finding in result.advanced_readability_checks
    )
    assert result.seo_checks
    assert result.readability_checks


@override_settings(SEO_NLP_MODEL="missing_test_model")
def test_load_failure_is_cached_once_and_exact_analysis_remains(caplog) -> None:
    reset_runtime_cache()
    try:
        first = analyze_page(make_page())
        second = analyze_page(make_page())

        assert first.nlp_warning == MODEL_UNAVAILABLE_WARNING
        assert second.nlp_warning == MODEL_UNAVAILABLE_WARNING
        assert runtime_info().load_attempts == 1
        assert all(
            finding.status == "unavailable"
            for finding in first.advanced_readability_checks
        )
        assert (
            len(
                [
                    record
                    for record in caplog.records
                    if "pipeline load failed" in record.message
                ]
            )
            == 1
        )
        assert first.seo_checks == second.seo_checks
    finally:
        reset_runtime_cache()
