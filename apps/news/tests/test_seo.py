from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from apps.news.models import NewsPage
from apps.news.seo import (
    analyze_page,
    contains_exact_phrase,
    count_exact_phrase,
    count_words,
    extract_content,
)


def stream_value(raw_body):
    return NewsPage._meta.get_field("body").stream_block.to_python(
        [
            {"type": block_type, "value": value, "id": None}
            for block_type, value in raw_body
        ],
    )


def make_page(
    *,
    title="Periodismo escolar en Arequipa",
    slug="periodismo-escolar-en-arequipa",
    seo_title="Periodismo escolar en Arequipa: guía editorial",
    search_description=(
        "El periodismo escolar en Arequipa fortalece la investigación, la "
        "escritura y la participación de equipos escolares en noticias locales."
    ),
    focus_keyphrase="periodismo escolar",
    summary="El periodismo escolar abre nuevas oportunidades de aprendizaje.",
    body=None,
    featured_image=True,
):
    raw_body = (
        body
        if body is not None
        else [
            (
                "paragraph",
                "<h2>Periodismo escolar y comunidad</h2>"
                "<p>El periodismo escolar ayuda a investigar hechos locales. "
                "La redacción contrasta fuentes y presenta información clara.</p>"
                '<p>Consulta <a linktype="page" id="2">otra noticia</a> y '
                '<a href="https://example.org/fuente">una fuente externa</a>.</p>',
            ),
        ]
    )
    return SimpleNamespace(
        title=title,
        slug=slug,
        seo_title=seo_title,
        search_description=search_description,
        focus_keyphrase=focus_keyphrase,
        summary=summary,
        body=stream_value(raw_body),
        featured_image=featured_image,
    )


def check_by_label(checks, label):
    return next(check for check in checks if check.label == label)


@pytest.mark.parametrize(
    ("value", "phrase"),
    [
        ("PERIODISMO ESCOLAR", "periodismo escolar"),
        ("Periodismo   escolar", "periodismo escolar"),
        ("El periodísmo escolar crece", "periodismo escolar"),
    ],
)
def test_exact_phrase_matching_normalizes_case_whitespace_and_accents(
    value,
    phrase,
) -> None:
    assert contains_exact_phrase(value, phrase)


def test_exact_phrase_matching_does_not_match_partial_words_or_synonyms() -> None:
    assert not contains_exact_phrase("periodismos escolares", "periodismo escolar")
    assert not contains_exact_phrase("prensa educativa", "periodismo escolar")
    assert contains_exact_phrase(
        "periodismo-escolar-en-arequipa",
        "periodismo escolar",
        slug=True,
    )


def test_exact_phrase_count_uses_normalized_exact_matches() -> None:
    assert (
        count_exact_phrase(
            "Periodismo escolar; PERIODÍSMO   ESCOLAR; periodismos escolares.",
            "periodismo escolar",
        )
        == 2
    )


def test_content_extraction_reads_paragraphs_headings_links_and_image_alt() -> None:
    body = stream_value(
        [
            (
                "paragraph",
                "<h2>Contexto local</h2>"
                "<p>Primer párrafo con evidencia.</p>"
                '<p><a linktype="page" id="2">Interno</a> '
                '<a href="https://example.org/source">Externo</a></p>',
            ),
            (
                "article_image",
                {
                    "image": None,
                    "caption": "Imagen ficticia",
                    "alt_text": "Mesa de redacción escolar",
                    "credit": "",
                },
            ),
        ],
    )

    snapshot = extract_content(body)

    assert snapshot.headings == ["Contexto local"]
    assert snapshot.paragraphs == [
        "Primer párrafo con evidencia.",
        "Interno Externo",
    ]
    assert snapshot.introduction == "Primer párrafo con evidencia."
    assert snapshot.body_image_alts == ["Mesa de redacción escolar"]
    assert [(link.linktype, link.href) for link in snapshot.links] == [
        ("page", ""),
        ("", "https://example.org/source"),
    ]


def test_nested_list_items_are_flattened_without_double_counting() -> None:
    outer_text = " ".join(["exterior"] * 140)
    inner_text = " ".join(["interior"] * 20)
    rich_text = f"<ul><li>{outer_text}<ul><li>{inner_text}</li></ul></li></ul>"
    body = stream_value(
        [
            (
                "paragraph",
                rich_text,
            ),
        ],
    )

    snapshot = extract_content(body)
    result = analyze_page(make_page(body=[("paragraph", rich_text)]))

    assert count_words(snapshot.text) == 160
    assert [count_words(paragraph) for paragraph in snapshot.paragraphs] == [20, 140]
    assert sum(count_words(event.text) for event in snapshot.events) == 160
    assert "exterior" in snapshot.text
    assert "interior" in snapshot.text
    assert (
        check_by_label(result.readability_checks, "Longitud de párrafos").status
        == "good"
    )
    assert (
        check_by_label(result.readability_checks, "Bloques de texto").status == "good"
    )


def test_seo_analysis_reports_expected_keyphrase_and_link_statuses() -> None:
    result = analyze_page(make_page(), site_hostname="school.test")

    assert check_by_label(result.seo_checks, "Frase clave objetivo").status == "good"
    assert (
        check_by_label(result.seo_checks, "Frase clave en el título SEO").status
        == "good"
    )
    assert check_by_label(result.seo_checks, "Frase clave en la URL").status == "good"
    assert (
        check_by_label(result.seo_checks, "Frase clave en subtítulos").status == "good"
    )
    assert check_by_label(result.seo_checks, "Enlace interno").status == "good"
    assert check_by_label(result.seo_checks, "Enlace externo").status == "good"


def test_missing_keyphrase_is_incomplete_and_dependent_checks_do_not_apply() -> None:
    result = analyze_page(make_page(focus_keyphrase=""))

    assert result.overall_label == "Incompleto"
    assert check_by_label(result.seo_checks, "Frase clave objetivo").status == "problem"
    assert (
        check_by_label(result.seo_checks, "Frase clave en el cuerpo").status
        == "not_applicable"
    )


def test_missing_native_seo_fields_are_problems_despite_fallbacks() -> None:
    result = analyze_page(
        make_page(
            seo_title="",
            search_description="",
        ),
    )

    assert result.overall_label == "Incompleto"
    assert (
        check_by_label(result.seo_checks, "Longitud del título SEO").status == "problem"
    )
    assert (
        check_by_label(result.seo_checks, "Longitud de la descripción meta").status
        == "problem"
    )


@pytest.mark.parametrize(
    ("length", "expected"),
    [(29, "warning"), (30, "good"), (60, "good"), (61, "warning"), (71, "problem")],
)
def test_title_length_boundaries(length, expected) -> None:
    result = analyze_page(make_page(seo_title="x" * length))
    assert (
        check_by_label(result.seo_checks, "Longitud del título SEO").status == expected
    )


@pytest.mark.parametrize(
    ("length", "expected"),
    [
        (119, "warning"),
        (120, "good"),
        (160, "good"),
        (161, "warning"),
        (181, "problem"),
    ],
)
def test_description_length_boundaries(length, expected) -> None:
    result = analyze_page(make_page(search_description="x" * length))
    assert (
        check_by_label(result.seo_checks, "Longitud de la descripción meta").status
        == expected
    )


def test_keyphrase_overuse_is_deterministic() -> None:
    repeated = " ".join(["periodismo escolar"] * 7 + ["contexto"] * 93)
    result = analyze_page(
        make_page(body=[("paragraph", f"<p>{repeated}.</p>")]),
    )

    assert (
        check_by_label(result.seo_checks, "Uso de la frase clave").status == "problem"
    )


@pytest.mark.parametrize(
    ("word_count", "expected"),
    [(149, "problem"), (150, "warning"), (299, "warning"), (300, "good")],
)
def test_article_word_count_boundaries(word_count, expected) -> None:
    words = " ".join(["contenido"] * word_count)
    result = analyze_page(
        make_page(body=[("paragraph", f"<p>{words}</p>")]),
    )

    assert (
        check_by_label(result.seo_checks, "Extensión del artículo").status == expected
    )


def test_body_image_alt_check_is_defensive_for_incomplete_drafts() -> None:
    result = analyze_page(
        make_page(
            body=[
                ("paragraph", "<p>Contenido de prueba.</p>"),
                (
                    "article_image",
                    {
                        "image": None,
                        "caption": "Pie ficticio",
                        "alt_text": "",
                        "credit": "",
                    },
                ),
            ],
        ),
    )

    assert (
        check_by_label(
            result.seo_checks,
            "Texto alternativo en imágenes del cuerpo",
        ).status
        == "problem"
    )


@pytest.mark.parametrize(
    ("paragraph_words", "expected"),
    [(150, "good"), (151, "warning"), (250, "warning"), (251, "problem")],
)
def test_readability_paragraph_boundaries(paragraph_words, expected) -> None:
    paragraph = " ".join(["palabra"] * paragraph_words) + "."
    result = analyze_page(
        make_page(body=[("paragraph", f"<p>{paragraph}</p>")]),
    )

    assert (
        check_by_label(result.readability_checks, "Longitud de párrafos").status
        == expected
    )


@pytest.mark.parametrize(
    ("long_sentence_count", "expected"),
    [(1, "good"), (2, "warning"), (3, "problem")],
)
def test_readability_sentence_ratio_boundaries(long_sentence_count, expected) -> None:
    long_sentence = " ".join(["palabra"] * 31) + "."
    short_sentence = "Texto breve y claro."
    sentences = [long_sentence] * long_sentence_count + [
        short_sentence,
    ] * (4 - long_sentence_count)
    result = analyze_page(
        make_page(body=[("paragraph", f"<p>{' '.join(sentences)}</p>")]),
    )

    assert (
        check_by_label(result.readability_checks, "Longitud de oraciones").status
        == expected
    )


def test_long_article_without_subheading_warns() -> None:
    paragraph = " ".join(["palabra"] * 320) + "."
    result = analyze_page(
        make_page(body=[("paragraph", f"<p>{paragraph}</p>")]),
    )

    assert (
        check_by_label(result.readability_checks, "Uso de subtítulos").status
        == "warning"
    )
    assert (
        check_by_label(result.readability_checks, "Bloques de texto").status
        == "warning"
    )


def test_acceptable_complete_article_can_reach_good_global_status() -> None:
    paragraphs = []
    for index in range(6):
        phrase = "periodismo escolar " if index == 0 else ""
        sentence = " ".join(["contenido"] * 12) + "."
        paragraphs.append(
            f"<p>{phrase}{sentence} {sentence} {sentence} {sentence}</p>",
        )
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
    assert all(
        check.status in {"good", "not_applicable"}
        for check in (*result.seo_checks, *result.readability_checks)
    )


def test_canonical_field_rejects_non_http_and_fragment_urls() -> None:
    field = NewsPage._meta.get_field("canonical_url")

    with pytest.raises(ValidationError):
        field.run_validators("ftp://example.org/news")
    with pytest.raises(ValidationError):
        field.run_validators("https://example.org/news#fragment")

    field.run_validators("https://example.org/news")
