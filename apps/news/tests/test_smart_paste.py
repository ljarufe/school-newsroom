import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.news.blocks import (
    TABLE_MAX_CAPTION_LENGTH,
    TABLE_MAX_CELL_LENGTH,
    TABLE_MAX_COLUMNS,
    TABLE_MAX_ROWS,
)
from apps.news.smart_paste import MAX_IMPORTED_BLOCKS, normalize_paste


def values(result) -> list[object]:
    return [block.value for block in result.blocks]


def test_html_paragraphs_become_separate_paragraph_blocks() -> None:
    result = normalize_paste(
        html_source="<p>Primer párrafo.</p><p>Segundo párrafo.</p>",
    )

    assert values(result) == [
        "<p>Primer párrafo.</p>",
        "<p>Segundo párrafo.</p>",
    ]
    assert result.as_dict()["summary"] == {
        "total": 2,
        "paragraphs": 2,
        "headings": 0,
        "lists": 0,
        "quotes": 0,
        "dividers": 0,
        "tables": 0,
    }


def test_html_headings_are_mapped_to_supported_paragraph_styles() -> None:
    result = normalize_paste(
        html_source=(
            "<h1>Título interno</h1><h2>Contexto</h2><h3>Detalle</h3>"
            "<h4>Dato</h4><h5>Más información</h5><h6>Cierre</h6>"
        ),
    )

    assert values(result) == [
        "<h2>Título interno</h2>",
        "<h2>Contexto</h2>",
        "<h3>Detalle</h3>",
        "<h4>Dato</h4>",
        "<h4>Más información</h4>",
        "<h4>Cierre</h4>",
    ]
    assert result.as_dict()["summary"]["headings"] == 6


def test_html_lists_keep_each_continuous_group_in_one_block() -> None:
    result = normalize_paste(
        html_source=(
            "<ol><li>Primero</li><li>Segundo</li></ol><ul><li>Uno</li><li>Dos</li></ul>"
        ),
    )

    assert values(result) == [
        "<ol><li>Primero</li><li>Segundo</li></ol>",
        "<ul><li>Uno</li><li>Dos</li></ul>",
    ]
    assert result.as_dict()["summary"]["lists"] == 2


def test_supported_inline_styles_and_safe_links_are_preserved() -> None:
    result = normalize_paste(
        html_source=(
            "<p><strong>Negrita</strong>, <em>cursiva</em> y "
            '<a href="https://example.invalid/fuente">enlace</a>. '
            '<span style="font-weight: 700; font-style: italic; color: red; '
            'font-family: serif; font-size: 24px">Estilo compatible</span></p>'
        ),
    )

    assert values(result) == [
        (
            "<p><strong>Negrita</strong>, <em>cursiva</em> y "
            '<a href="https://example.invalid/fuente">enlace</a>. '
            "<strong><em>Estilo compatible</em></strong></p>"
        )
    ]
    assert "style=" not in values(result)[0]


def test_supported_styles_declared_on_block_elements_are_preserved() -> None:
    result = normalize_paste(
        html_source=(
            '<p style="font-weight: 700">Párrafo destacado</p>'
            '<h3 style="font-style: italic">Encabezado enfatizado</h3>'
        ),
    )

    assert values(result) == [
        "<p><strong>Párrafo destacado</strong></p>",
        "<h3><em>Encabezado enfatizado</em></h3>",
    ]


def test_normal_weight_overrides_semantic_bold_elements() -> None:
    result = normalize_paste(
        html_source=(
            '<p><b style="font-weight: normal">Texto normal</b> y '
            '<strong style="font-weight: 400">otro texto normal</strong>; '
            '<strong style="font-weight: normal; font-style: italic">'
            "sólo cursiva</strong>.</p>"
        ),
    )

    assert values(result) == [
        "<p>Texto normal y otro texto normal; <em>sólo cursiva</em>.</p>"
    ]


def test_blockquote_and_horizontal_rule_remain_supported_blocks() -> None:
    result = normalize_paste(
        html_source=(
            "<blockquote><p>Una cita</p><p>Segunda línea</p></blockquote><hr>"
        ),
    )

    assert values(result) == [
        "<blockquote>Una cita<br/>Segunda línea</blockquote>",
        "<hr/>",
    ]
    assert result.as_dict()["summary"]["quotes"] == 1
    assert result.as_dict()["summary"]["dividers"] == 1


def test_word_and_google_docs_noise_is_removed_without_losing_semantics() -> None:
    result = normalize_paste(
        html_source=(
            '<!-- comentario interno --><div class="docs-internal-guid-123">'
            '<p class="MsoNormal" style="margin: 0; color: blue">'
            '<span lang="es" style="font-family: Arial">Texto </span>'
            '<b style="font-size: 18px">editorial</b></p>'
            "<p><del>versión descartada</del><ins>versión vigente</ins></p>"
            "</div>"
        ),
    )

    assert values(result) == [
        "<p>Texto <strong>editorial</strong></p>",
        "<p>versión vigente</p>",
    ]
    combined = "".join(values(result))
    assert "class=" not in combined
    assert "style=" not in combined
    assert "versión descartada" not in combined
    assert "Se eliminaron marcas de control de cambios del documento." in (
        result.warnings
    )


def test_plain_text_uses_nonempty_lines_without_guessing_headings() -> None:
    result = normalize_paste(
        plain_text=(
            "TÍTULO EN MAYÚSCULAS\n"
            "segunda línea del mismo segmento\n\n"
            "Párrafo independiente."
        ),
    )

    assert result.source == "plain"
    assert values(result) == [
        "<p>TÍTULO EN MAYÚSCULAS</p>",
        "<p>segunda línea del mismo segmento</p>",
        "<p>Párrafo independiente.</p>",
    ]
    assert all("<h" not in value for value in values(result))


def test_plain_text_creates_one_block_per_nonempty_line() -> None:
    result = normalize_paste(
        plain_text="Primera línea.\nSegunda línea.\n\nTercera línea.",
    )

    assert values(result) == [
        "<p>Primera línea.</p>",
        "<p>Segunda línea.</p>",
        "<p>Tercera línea.</p>",
    ]


def test_inline_wrapper_with_nested_blocks_is_structurally_transparent() -> None:
    result = normalize_paste(
        html_source=(
            "<span><b style='font-weight: normal'>"
            "<h2>Primer título</h2>"
            "<h3>Segundo título</h3>"
            "<p>Primer párrafo con <strong>negrita real</strong>.</p>"
            "<p>Segundo párrafo con <em>cursiva real</em>.</p>"
            "<ul><li>Primera viñeta</li><li>Segunda viñeta</li></ul>"
            "</b></span>"
        ),
    )

    assert values(result) == [
        "<h2>Primer título</h2>",
        "<h3>Segundo título</h3>",
        "<p>Primer párrafo con <strong>negrita real</strong>.</p>",
        "<p>Segundo párrafo con <em>cursiva real</em>.</p>",
        "<ul><li>Primera viñeta</li><li>Segunda viñeta</li></ul>",
    ]
    assert "<strong><h" not in "".join(values(result))


def test_inline_wrapper_preserves_spaces_between_inline_siblings() -> None:
    result = normalize_paste(
        html_source="<span><span>Texto entre</span> <em>wrappers</em></span>",
    )

    assert values(result) == ["<p>Texto entre <em>wrappers</em></p>"]


def test_word_boundary_noise_is_trimmed_without_losing_internal_markup() -> None:
    result = normalize_paste(
        html_source=(
            "<p>&nbsp;<span><strong> </strong><br/>"
            "Texto <em>interno</em><br/>segunda línea"
            "<i>&nbsp;</i><br/></span><o:p>&nbsp;</o:p></p>"
            "<h3><span>&nbsp;<br/></span>Título <strong>útil</strong>"
            "<span><br/>&nbsp;</span></h3>"
        ),
    )

    assert values(result) == [
        "<p>Texto <em>interno</em><br/>segunda línea</p>",
        "<h3>Título <strong>útil</strong></h3>",
    ]


@pytest.mark.parametrize(
    ("html_source", "expected"),
    [
        (
            "<p>&nbsp;&nbsp;Texto inicial.</p>",
            "<p>Texto inicial.</p>",
        ),
        (
            "<p><span>&nbsp;Texto <strong>interno</strong>&nbsp;</span></p>",
            "<p>Texto <strong>interno</strong></p>",
        ),
        (
            "<h3><span> &nbsp;Título útil&nbsp; </span></h3>",
            "<h3>Título útil</h3>",
        ),
    ],
)
def test_mixed_boundary_text_is_trimmed_recursively(
    html_source: str,
    expected: str,
) -> None:
    result = normalize_paste(html_source=html_source)

    assert values(result) == [expected]


def test_mixed_boundary_trim_keeps_meaningful_interior_spacing_and_breaks() -> None:
    result = normalize_paste(
        html_source=(
            "<p><span>&nbsp;Texto</span> <strong>con formato</strong> "
            "<a href='https://example.invalid'>y enlace</a><br/>"
            "<em>en otra línea&nbsp;</em></p>"
        ),
    )

    assert values(result) == [
        (
            "<p>Texto <strong>con formato</strong> "
            '<a href="https://example.invalid">y enlace</a><br/>'
            "<em>en otra línea</em></p>"
        )
    ]


def test_empty_word_auxiliary_paragraph_does_not_create_a_block() -> None:
    result = normalize_paste(
        html_source=(
            '<p class="MsoNormal"><span>&nbsp;<o:p>&nbsp;</o:p><br/></span></p>'
            "<p>Contenido real.</p>"
        ),
    )

    assert values(result) == ["<p>Contenido real.</p>"]


def test_representative_word_sample_keeps_editorial_elements_separate() -> None:
    # Minimal HTML derived from the sample's OOXML structure. This is not a
    # claim about the exact clipboard HTML produced by Microsoft Word.
    result = normalize_paste(
        html_source=(
            "<b style='font-weight: normal'>"
            "<h1>Anuncian actividades por el Día Nacional del Pisco</h1>"
            "<p><br></p><p><br></p>"
            "<p>Festival regional. <strong>Promueve la identidad.</strong></p>"
            "<p>Habrá degustaciones. <strong>También una clase magistral.</strong></p>"
            "<p>Arequipa conserva una producción tradicional.</p>"
            "<h2>Reducción de ventas</h2>"
            "<p>Las ventas cayeron. <strong>Falta fiscalización.</strong></p>"
            "<p>Las catas ayudan a reconocer un producto original.</p>"
            "<h2>Proyecciones agrícolas ante el fenómeno de El Niño</h2>"
            "<p>La cosecha de uva culminó de manera regular.</p>"
            "<p>La escasez de agua es el principal riesgo.</p>"
            "<p></p>"
            "</b>"
        ),
    )

    assert values(result) == [
        "<h2>Anuncian actividades por el Día Nacional del Pisco</h2>",
        "<p>Festival regional. <strong>Promueve la identidad.</strong></p>",
        "<p>Habrá degustaciones. <strong>También una clase magistral.</strong></p>",
        "<p>Arequipa conserva una producción tradicional.</p>",
        "<h2>Reducción de ventas</h2>",
        "<p>Las ventas cayeron. <strong>Falta fiscalización.</strong></p>",
        "<p>Las catas ayudan a reconocer un producto original.</p>",
        "<h2>Proyecciones agrícolas ante el fenómeno de El Niño</h2>",
        "<p>La cosecha de uva culminó de manera regular.</p>",
        "<p>La escasez de agua es el principal riesgo.</p>",
    ]


def test_scripts_iframes_and_unsafe_links_are_discarded() -> None:
    result = normalize_paste(
        html_source=(
            "<p>Texto seguro<script>alert('x')</script>"
            '<a href="javascript:alert(1)" onclick="alert(2)">enlace riesgoso</a>'
            '<a href="http://[">enlace malformado</a>'
            '</p><iframe src="https://example.invalid/embed"></iframe>'
        ),
    )

    assert values(result) == ["<p>Texto seguroenlace riesgosoenlace malformado</p>"]
    combined = "".join(values(result))
    assert "script" not in combined
    assert "iframe" not in combined
    assert "javascript:" not in combined
    assert "onclick" not in combined
    assert "Se quitaron destinos de enlace no seguros y se conservó su texto." in (
        result.warnings
    )
    assert "Se descartó contenido no compatible o potencialmente inseguro." in (
        result.warnings
    )


@pytest.mark.parametrize(
    ("html_source", "plain_text"),
    [
        ("", ""),
        ("   ", "\n \n"),
        ("<p><br></p>", ""),
        ("<!-- sólo comentario -->", ""),
    ],
)
def test_empty_content_does_not_create_blocks(
    html_source: str,
    plain_text: str,
) -> None:
    result = normalize_paste(
        html_source=html_source,
        plain_text=plain_text,
    )

    assert result.blocks == []


def test_html_source_does_not_fall_back_to_plain_text_after_discarding_image() -> None:
    result = normalize_paste(
        html_source='<img src="https://example.invalid/external.jpg">',
        plain_text="Texto alternativo que no debe convertirse en párrafo.",
    )

    assert result.source == "html"
    assert result.blocks == []
    assert "Se descartó una imagen; agrégala manualmente desde el CMS." in (
        result.warnings
    )


def test_nested_lists_flatten_to_one_level_without_losing_item_text() -> None:
    result = normalize_paste(
        html_source=(
            "<ol><li>Primero<ol><li>Primero A</li><li>Primero B"
            "<ul><li>Detalle</li></ul></li></ol></li>"
            "<li>Segundo</li></ol>"
        ),
    )

    assert values(result) == [
        (
            "<ol><li>Primero</li><li>Primero A</li><li>Primero B</li>"
            "<li>Detalle</li><li>Segundo</li></ol>"
        )
    ]
    assert (
        "Las listas anidadas se aplanaron; revisa su orden antes de publicar."
        in result.warnings
    )


def test_simple_table_becomes_an_independent_table_block_with_caption() -> None:
    result = normalize_paste(
        html_source=(
            "<p>Antes.</p><table><caption>Resultados ficticios</caption>"
            "<thead><tr><th>Nombre</th><th>Valor</th></tr></thead>"
            "<tbody><tr><td>Dato</td><td>10</td></tr></tbody></table>"
            "<p>Después.</p>"
        ),
    )

    assert [block.block_type for block in result.blocks] == [
        "paragraph",
        "table",
        "paragraph",
    ]
    table = result.blocks[1].value
    assert table == {
        "data": [["Nombre", "Valor"], ["Dato", "10"]],
        "table_caption": "Resultados ficticios",
        "table_header_choice": "row",
        "first_row_is_table_header": True,
        "first_col_is_header": False,
    }
    assert result.as_dict()["summary"]["tables"] == 1


def test_reference_valley_table_keeps_exact_four_by_four_matrix() -> None:
    result = normalize_paste(
        html_source=(
            "<table>"
            "<tr><th>Valle / variedad</th><th>Quebranta</th>"
            "<th>Italia</th><th>Moscatel</th></tr>"
            "<tr><td>Vítor</td><td>120 000 L</td><td>42 000 L</td>"
            "<td>18 000 L</td></tr>"
            "<tr><td>Majes</td><td>95 000 L</td><td>51 000 L</td>"
            "<td>22 000 L</td></tr>"
            "<tr><td>Caravelí</td><td>70 000 L</td><td>33 000 L</td>"
            "<td>27 000 L</td></tr>"
            "</table>"
        ),
    )

    assert result.blocks[0].value == {
        "data": [
            ["Valle / variedad", "Quebranta", "Italia", "Moscatel"],
            ["Vítor", "120 000 L", "42 000 L", "18 000 L"],
            ["Majes", "95 000 L", "51 000 L", "22 000 L"],
            ["Caravelí", "70 000 L", "33 000 L", "27 000 L"],
        ],
        "table_caption": "",
        "table_header_choice": "row",
        "first_row_is_table_header": True,
        "first_col_is_header": False,
    }


def test_table_detects_unambiguous_row_and_column_headers() -> None:
    result = normalize_paste(
        html_source=(
            "<table><thead><tr><th>Zona</th><th>Total</th></tr></thead>"
            "<tbody><tr><th scope='row'>Norte</th><td>4</td></tr>"
            "<tr><th scope='row'>Sur</th><td>6</td></tr></tbody></table>"
        ),
    )

    table = result.blocks[0].value
    assert table["table_header_choice"] == "both"
    assert table["first_row_is_table_header"] is True
    assert table["first_col_is_header"] is True


def test_table_cells_keep_safe_text_and_discard_unsafe_content() -> None:
    result = normalize_paste(
        html_source=(
            "<table><tr><td>Dato<script>alert(1)</script>"
            "<img src='https://example.invalid/x.jpg'></td>"
            "<td><form>secreto</form>Visible</td></tr></table>"
        ),
    )

    table = result.blocks[0].value
    assert table["data"] == [["Dato", "Visible"]]
    assert "alert" not in str(table)
    assert "secreto" not in str(table)
    assert "Se descartó una imagen; agrégala manualmente desde el CMS." in (
        result.warnings
    )
    assert "Se descartó contenido no compatible o potencialmente inseguro." in (
        result.warnings
    )


def test_nested_table_text_is_kept_with_explicit_separation() -> None:
    result = normalize_paste(
        html_source=(
            "<table><tr><th>Dato</th><th>Detalle</th></tr>"
            "<tr><td>Control</td><td><table>"
            "<tr><td>Aroma</td><td>Aprobado</td></tr>"
            "<tr><td>Sabor</td><td>Aprobado</td></tr>"
            "</table></td></tr></table>"
        ),
    )

    assert result.blocks[0].value["data"] == [
        ["Dato", "Detalle"],
        ["Control", "Aroma Aprobado Sabor Aprobado"],
    ]
    assert (
        "Las celdas combinadas o tablas anidadas se simplificaron; "
        "revisa la tabla antes de publicar." in result.warnings
    )


def test_complex_and_irregular_tables_degrade_deterministically() -> None:
    result = normalize_paste(
        html_source=(
            "<table><tr><td rowspan='2'>A</td><td>B</td></tr>"
            "<tr><td>C<table><tr><td>Anidado</td></tr></table></td>"
            "<td>D</td><td>E</td></tr>"
            "</table>"
        ),
    )

    table = result.blocks[0].value
    assert table["data"] == [
        ["A", "B", "", ""],
        ["", "C Anidado", "D", "E"],
    ]
    assert (
        "Las celdas combinadas o tablas anidadas se simplificaron; "
        "revisa la tabla antes de publicar." in result.warnings
    )
    assert "Las filas irregulares se completaron con celdas vacías." in (
        result.warnings
    )


def test_colspan_uses_empty_continuations_and_preserves_following_columns() -> None:
    result = normalize_paste(
        html_source=(
            "<table><tr><th colspan='3'>Resumen</th></tr>"
            "<tr><td>Valle</td><td>Mes</td><td>Producción</td></tr></table>"
        ),
    )

    assert result.blocks[0].value["data"] == [
        ["Resumen", "", ""],
        ["Valle", "Mes", "Producción"],
    ]
    assert (
        "Las celdas combinadas o tablas anidadas se simplificaron; "
        "revisa la tabla antes de publicar." in result.warnings
    )


def test_table_import_limits_are_applied_with_a_warning() -> None:
    oversized_cell = "x" * (TABLE_MAX_CELL_LENGTH + 1)
    rows = [
        "<tr>"
        + "".join(
            f"<td>{oversized_cell if row == 0 and column == 0 else 'dato'}</td>"
            for column in range(TABLE_MAX_COLUMNS + 1)
        )
        + "</tr>"
        for row in range(TABLE_MAX_ROWS + 1)
    ]
    caption = "c" * (TABLE_MAX_CAPTION_LENGTH + 1)

    result = normalize_paste(
        html_source=f"<table><caption>{caption}</caption>{''.join(rows)}</table>",
    )

    table = result.blocks[0].value
    assert len(table["data"]) == TABLE_MAX_ROWS
    assert all(len(row) == TABLE_MAX_COLUMNS for row in table["data"])
    assert len(table["data"][0][0]) == TABLE_MAX_CELL_LENGTH
    assert len(table["table_caption"]) == TABLE_MAX_CAPTION_LENGTH
    assert (
        "Una tabla superó los límites de importación y se recortó de forma segura."
        in result.warnings
    )


def test_plain_text_import_limits_block_count() -> None:
    result = normalize_paste(
        plain_text="\n\n".join(
            f"Párrafo {index}" for index in range(MAX_IMPORTED_BLOCKS + 1)
        ),
    )

    assert len(result.blocks) == MAX_IMPORTED_BLOCKS
    assert (
        f"Se importaron como máximo {MAX_IMPORTED_BLOCKS} bloques; "
        "el contenido adicional se descartó." in result.warnings
    )


def add_admin_access_permission(user) -> None:
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtailadmin",
            codename="access_admin",
        )
    )


@pytest.mark.django_db
def test_normalize_endpoint_requires_full_editorial_surface_permission() -> None:
    allowed_user = get_user_model().objects.create_user(
        username="smart-paste-director",
        password="test-password",
    )
    allowed_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="news",
            codename="access_full_editorial_surfaces",
        )
    )
    add_admin_access_permission(allowed_user)
    denied_user = get_user_model().objects.create_user(
        username="smart-paste-curator",
        password="test-password",
    )
    add_admin_access_permission(denied_user)
    endpoint = reverse("news_smart_paste_normalize")
    client = Client()

    client.force_login(allowed_user)
    allowed_response = client.post(
        endpoint,
        data=json.dumps(
            {
                "html": (
                    "<h1>Título</h1><table><tr><th>Dato</th></tr>"
                    "<tr><td>10</td></tr></table>"
                ),
                "text": "",
            }
        ),
        content_type="application/json",
    )

    client.force_login(denied_user)
    denied_response = client.post(
        endpoint,
        data=json.dumps({"html": "<p>No autorizado.</p>", "text": ""}),
        content_type="application/json",
    )

    assert allowed_response.status_code == 200
    response_blocks = allowed_response.json()["blocks"]
    assert [block["type"] for block in response_blocks] == [
        "paragraph",
        "table",
    ]
    paragraph_state = json.loads(response_blocks[0]["value"])
    assert paragraph_state["blocks"][0]["type"] == "header-two"
    assert paragraph_state["blocks"][0]["text"] == "Título"
    assert response_blocks[1]["value"]["data"] == [["Dato"], ["10"]]
    assert denied_response.status_code == 302
    assert denied_response.url == reverse("wagtailadmin_home")


@pytest.mark.django_db
def test_normalize_endpoint_is_post_only_and_csrf_protected() -> None:
    user = get_user_model().objects.create_user(
        username="smart-paste-security",
        password="test-password",
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="news",
            codename="access_full_editorial_surfaces",
        )
    )
    add_admin_access_permission(user)
    endpoint = reverse("news_smart_paste_normalize")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    get_response = client.get(endpoint)
    post_without_csrf = client.post(
        endpoint,
        data=json.dumps({"html": "<p>Texto.</p>", "text": ""}),
        content_type="application/json",
    )

    assert get_response.status_code == 405
    assert post_without_csrf.status_code == 403


@pytest.mark.django_db
def test_normalize_endpoint_rejects_invalid_and_oversized_payloads() -> None:
    user = get_user_model().objects.create_superuser(
        username="smart-paste-admin",
        email="smart-paste-admin@example.invalid",
        password="test-password",
    )
    client = Client()
    client.force_login(user)
    endpoint = reverse("news_smart_paste_normalize")

    invalid_response = client.post(
        endpoint,
        data="{",
        content_type="application/json",
    )
    oversized_response = client.post(
        endpoint,
        data=json.dumps({"html": "", "text": "x" * 1_000_001}),
        content_type="application/json",
    )

    assert invalid_response.status_code == 400
    assert invalid_response.json()["error"] == "No se pudo leer el contenido pegado."
    assert oversized_response.status_code == 400
    assert "demasiado extensa" in oversized_response.json()["error"]
