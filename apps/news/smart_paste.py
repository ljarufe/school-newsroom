import re
from collections import Counter
from dataclasses import dataclass, field
from html import escape
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from .blocks import (
    TABLE_MAX_CAPTION_LENGTH,
    TABLE_MAX_CELL_LENGTH,
    TABLE_MAX_COLUMNS,
    TABLE_MAX_ROWS,
)

MAX_IMPORTED_BLOCKS = 500
BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "iframe",
    "img",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "script",
    "section",
    "style",
    "table",
    "ul",
}
STRUCTURAL_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}
CONTAINER_TAGS = {
    "article",
    "aside",
    "body",
    "footer",
    "header",
    "html",
    "main",
    "nav",
    "section",
}
DISCARDED_CONTENT_TAGS = {
    "applet",
    "audio",
    "canvas",
    "embed",
    "form",
    "iframe",
    "noscript",
    "object",
    "script",
    "style",
    "svg",
    "template",
    "video",
}
METADATA_TAGS = {"base", "head", "link", "meta", "title"}
HEADING_MAP = {
    "h1": "h2",
    "h2": "h2",
    "h3": "h3",
    "h4": "h4",
    "h5": "h4",
    "h6": "h4",
}
SAFE_LINK_SCHEMES = {"", "http", "https", "mailto"}


@dataclass(frozen=True)
class NormalizedBlock:
    block_type: str
    value: str | dict[str, object]
    kind: str

    def as_dict(self) -> dict[str, object]:
        return {"type": self.block_type, "value": self.value}


@dataclass
class NormalizedPaste:
    blocks: list[NormalizedBlock]
    source: str
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        counts = Counter(block.kind for block in self.blocks)
        return {
            "blocks": [block.as_dict() for block in self.blocks],
            "source": self.source,
            "summary": {
                "total": len(self.blocks),
                "paragraphs": counts["paragraph"],
                "headings": counts["heading"],
                "lists": counts["list"],
                "quotes": counts["quote"],
                "dividers": counts["divider"],
                "tables": counts["table"],
            },
            "warnings": self.warnings,
        }


class HtmlPasteNormalizer:
    """Convert untrusted clipboard HTML into supported StreamField blocks."""

    def __init__(self) -> None:
        self.blocks: list[NormalizedBlock] = []
        self.discarded = Counter()

    def normalize(self, source: str) -> NormalizedPaste:
        self.blocks = []
        self.discarded.clear()
        soup = BeautifulSoup(source, "html.parser")
        root = soup.body or soup
        self._walk_container(root)
        return NormalizedPaste(
            blocks=self.blocks,
            source="html",
            warnings=self._warnings(),
        )

    def _walk_container(self, container: Tag) -> None:
        pending_inline: list[NavigableString | Tag] = []

        def flush_inline() -> None:
            if not pending_inline:
                return
            rendered = self._trim_rendered_boundaries(
                "".join(self._render_inline(node) for node in pending_inline)
            )
            self._append_rich_text("paragraph", f"<p>{rendered}</p>")
            pending_inline.clear()

        for child in container.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                if str(child):
                    pending_inline.append(child)
                continue
            if not isinstance(child, Tag):
                continue

            name = child.name.lower()
            if name in METADATA_TAGS:
                continue
            if name not in BLOCK_TAGS:
                if self._contains_structural_block_descendant(child):
                    flush_inline()
                    self._walk_container(child)
                    continue
                pending_inline.append(child)
                continue

            flush_inline()
            self._handle_block(child)

        flush_inline()

    def _handle_block(self, node: Tag) -> None:
        name = node.name.lower()

        if name in CONTAINER_TAGS:
            self._walk_container(node)
            return

        if name == "div":
            if self._contains_structural_block_descendant(node):
                self._walk_container(node)
            else:
                rendered = self._render_trimmed_children(node)
                self._append_rich_text(
                    "paragraph",
                    f"<p>{rendered}</p>",
                )
            return

        if name == "p":
            rendered = self._render_trimmed_children(node)
            self._append_rich_text(
                "paragraph",
                f"<p>{rendered}</p>",
            )
            return

        if name in HEADING_MAP:
            output_name = HEADING_MAP[name]
            rendered = self._render_trimmed_children(node)
            self._append_rich_text(
                "heading",
                f"<{output_name}>{rendered}</{output_name}>",
            )
            return

        if name in {"ol", "ul"}:
            self._append_list(node)
            return

        if name == "blockquote":
            parts = []
            for child in node.children:
                if isinstance(child, Tag) and child.name.lower() in {"div", "p"}:
                    rendered = self._render_trimmed_children(child)
                else:
                    rendered = self._trim_rendered_boundaries(
                        self._render_inline(child)
                    )
                if rendered:
                    parts.append(rendered)
            self._append_rich_text(
                "quote",
                f"<blockquote>{'<br/>'.join(parts)}</blockquote>",
            )
            return

        if name == "hr":
            self._append_rich_text("divider", "<hr/>")
            return

        if name == "table":
            self._append_table(node)
            return

        if name == "pre":
            self.discarded["code"] += 1
            text = self._safe_plain_text(node)
            self._append_rich_text("paragraph", f"<p>{escape(text)}</p>")
            return

        if name == "img":
            self.discarded["images"] += 1
            return

        if name in DISCARDED_CONTENT_TAGS:
            self.discarded["unsafe_elements"] += 1
            return

        if name == "figure":
            self.discarded["images"] += len(node.find_all("img"))
            caption = node.find("figcaption")
            if caption is not None:
                rendered = self._render_trimmed_children(caption)
                self._append_rich_text(
                    "paragraph",
                    f"<p>{rendered}</p>",
                )
            return

        text = self._render_trimmed_children(node)
        if text:
            self.discarded["unsupported_blocks"] += 1
            self._append_rich_text("paragraph", f"<p>{text}</p>")

    def _append_list(self, node: Tag) -> None:
        name = node.name.lower()
        items = self._flatten_list_items(node)

        if items:
            markup = "".join(f"<li>{item}</li>" for item in items)
            self._append_rich_text("list", f"<{name}>{markup}</{name}>")
            return

        text = self._safe_plain_text(node)
        self._append_rich_text("paragraph", f"<p>{escape(text)}</p>")

    def _flatten_list_items(self, node: Tag) -> list[str]:
        flattened: list[str] = []
        for item in node.find_all("li", recursive=False):
            nested_lists = [
                child
                for child in item.children
                if isinstance(child, Tag) and child.name.lower() in {"ol", "ul"}
            ]
            content = self._trim_rendered_boundaries(
                "".join(
                    self._render_inline(child)
                    for child in item.children
                    if child not in nested_lists
                )
            )
            if content:
                flattened.append(content)
            for nested_list in nested_lists:
                self.discarded["nested_lists"] += 1
                flattened.extend(self._flatten_list_items(nested_list))
        return flattened

    def _append_table(self, node: Tag) -> None:
        rows = [row for row in node.find_all("tr") if row.find_parent("table") is node]
        if not rows:
            self.discarded["empty_tables"] += 1
            return

        if node.find("table") is not None:
            self.discarded["complex_tables"] += 1

        row_cells = [
            row.find_all(["td", "th"], recursive=False) for row in rows[:TABLE_MAX_ROWS]
        ]
        if len(rows) > TABLE_MAX_ROWS:
            self.discarded["table_limits"] += 1

        if any(
            cell.has_attr("rowspan") or cell.has_attr("colspan")
            for cells in row_cells
            for cell in cells
        ):
            self.discarded["complex_tables"] += 1

        data: list[list[str]] = []
        reserved_columns: dict[int, set[int]] = {}
        row_widths: list[int] = []
        for row_index, cells in enumerate(row_cells):
            occupied = reserved_columns.get(row_index, set())
            normalized_row = [""] * (max(occupied, default=-1) + 1)
            column_index = 0
            for cell in cells:
                while column_index in occupied:
                    column_index += 1
                if column_index >= TABLE_MAX_COLUMNS:
                    self.discarded["table_limits"] += 1
                    break

                colspan = self._positive_span(cell.get("colspan"))
                rowspan = self._positive_span(cell.get("rowspan"))
                available_span = min(colspan, TABLE_MAX_COLUMNS - column_index)
                if available_span < colspan:
                    self.discarded["table_limits"] += 1

                text = self._safe_plain_text(cell)
                if len(text) > TABLE_MAX_CELL_LENGTH:
                    text = text[:TABLE_MAX_CELL_LENGTH].rstrip()
                    self.discarded["table_limits"] += 1

                required_width = column_index + available_span
                normalized_row.extend([""] * (required_width - len(normalized_row)))
                normalized_row[column_index] = text

                final_spanned_row = min(
                    row_index + rowspan,
                    len(row_cells),
                )
                for future_row in range(row_index + 1, final_spanned_row):
                    reservations = reserved_columns.setdefault(future_row, set())
                    reservations.update(
                        range(column_index, column_index + available_span)
                    )
                column_index += available_span

            row_widths.append(len(normalized_row))
            data.append(normalized_row)

        max_columns = min(max(row_widths, default=0), TABLE_MAX_COLUMNS)
        if max_columns == 0:
            self.discarded["empty_tables"] += 1
            return
        if len(set(row_widths)) > 1:
            self.discarded["irregular_tables"] += 1
        for normalized_row in data:
            del normalized_row[max_columns:]
            normalized_row.extend([""] * (max_columns - len(normalized_row)))

        caption_node = node.find("caption", recursive=False)
        caption = self._safe_plain_text(caption_node) if caption_node else ""
        if len(caption) > TABLE_MAX_CAPTION_LENGTH:
            caption = caption[:TABLE_MAX_CAPTION_LENGTH].rstrip()
            self.discarded["table_limits"] += 1

        first_row_cells = row_cells[0]
        in_thead = rows[0].find_parent("thead") is not None
        first_row_is_header = (
            in_thead
            or bool(first_row_cells)
            and all(cell.name.lower() == "th" for cell in first_row_cells)
        )
        body_row_cells = row_cells[1:] if first_row_is_header else row_cells
        first_col_is_header = bool(body_row_cells) and all(
            cells
            and cells[0].name.lower() == "th"
            and (cells[0].get("scope") or "row").lower() != "col"
            for cells in body_row_cells
        )

        if first_row_is_header and first_col_is_header:
            header_choice = "both"
        elif first_row_is_header:
            header_choice = "row"
        elif first_col_is_header:
            header_choice = "column"
        else:
            header_choice = "neither"

        self._append_block(
            NormalizedBlock(
                block_type="table",
                kind="table",
                value={
                    "data": data,
                    "table_caption": caption,
                    "table_header_choice": header_choice,
                    "first_row_is_table_header": first_row_is_header,
                    "first_col_is_header": first_col_is_header,
                },
            )
        )

    def _render_children(self, node: Tag) -> str:
        return "".join(self._render_inline(child) for child in node.children)

    def _render_trimmed_children(self, node: Tag) -> str:
        return self._trim_rendered_boundaries(self._render_children(node))

    @classmethod
    def _trim_rendered_boundaries(cls, rendered: str) -> str:
        fragment = BeautifulSoup(f"<div>{rendered}</div>", "html.parser").div
        if fragment is None:
            return ""

        cls._trim_boundary_edge(fragment, from_start=True)
        cls._trim_boundary_edge(fragment, from_start=False)
        return "".join(str(child) for child in fragment.children)

    @classmethod
    def _trim_boundary_edge(cls, container: Tag, *, from_start: bool) -> None:
        while container.contents:
            edge = container.contents[0 if from_start else -1]
            if isinstance(edge, NavigableString) and not isinstance(edge, Comment):
                text = str(edge)
                trimmed = (
                    text.lstrip(" \t\r\n\f\v\xa0")
                    if from_start
                    else text.rstrip(" \t\r\n\f\v\xa0")
                )
                if trimmed:
                    if trimmed != text:
                        edge.replace_with(trimmed)
                    break
                edge.extract()
                continue
            if cls._is_boundary_noise(edge):
                edge.extract()
                continue
            if isinstance(edge, Tag) and edge.name.lower() in {
                "a",
                "em",
                "i",
                "span",
                "strong",
            }:
                cls._trim_boundary_edge(edge, from_start=from_start)
                if cls._is_boundary_noise(edge):
                    edge.extract()
                    continue
            break

    @classmethod
    def _is_boundary_noise(cls, node) -> bool:
        if isinstance(node, Comment):
            return True
        if isinstance(node, NavigableString):
            return not str(node).replace("\xa0", " ").strip()
        if not isinstance(node, Tag):
            return True
        if node.name.lower() == "br":
            return True
        return all(cls._is_boundary_noise(child) for child in node.children)

    def _render_inline(self, node) -> str:
        if isinstance(node, Comment):
            return ""
        if isinstance(node, NavigableString):
            return escape(self._normalize_text(str(node)), quote=False)
        if not isinstance(node, Tag):
            return ""

        name = node.name.lower()
        if name in METADATA_TAGS:
            return ""
        if name == "img":
            self.discarded["images"] += 1
            return ""
        if name in DISCARDED_CONTENT_TAGS:
            self.discarded["unsafe_elements"] += 1
            return ""
        if name == "del":
            self.discarded["tracked_changes"] += 1
            return ""

        rendered = self._render_children(node)
        if name == "br":
            return "<br/>"
        if name == "a":
            href = (node.get("href") or "").strip()
            if self._is_safe_href(href):
                return f'<a href="{escape(href, quote=True)}">{rendered}</a>'
            self.discarded["unsafe_links"] += 1
            return rendered
        if name in {"b", "strong"}:
            return f"<strong>{rendered}</strong>"
        if name in {"em", "i"}:
            return f"<em>{rendered}</em>"
        if name == "ins":
            self.discarded["tracked_changes"] += 1
            return rendered

        is_bold, is_italic = self._semantic_inline_styles(node.get("style", ""))
        if is_italic:
            rendered = f"<em>{rendered}</em>"
        if is_bold:
            rendered = f"<strong>{rendered}</strong>"
        return rendered

    def _safe_plain_text(self, node: Tag | None) -> str:
        if node is None:
            return ""
        chunks: list[str] = []

        def walk(child) -> None:
            if isinstance(child, Comment):
                return
            if isinstance(child, NavigableString):
                chunks.append(str(child))
                return
            if not isinstance(child, Tag):
                return

            name = child.name.lower()
            if name == "img":
                self.discarded["images"] += 1
                return
            if name in DISCARDED_CONTENT_TAGS or name in METADATA_TAGS:
                self.discarded["unsafe_elements"] += 1
                return
            if name == "del":
                self.discarded["tracked_changes"] += 1
                return
            if name == "ins":
                self.discarded["tracked_changes"] += 1
            if name == "br":
                chunks.append(" ")
                return
            if name in {"div", "li", "p", "table", "td", "th", "tr"}:
                chunks.append(" ")
            for nested in child.children:
                walk(nested)
            if name in {"div", "li", "p", "table", "td", "th", "tr"}:
                chunks.append(" ")

        for child in node.children:
            walk(child)
        return self._normalize_text("".join(chunks)).strip()

    def _append_rich_text(self, kind: str, value: str) -> None:
        fragment = BeautifulSoup(value, "html.parser")
        has_text = bool(fragment.get_text(" ", strip=True))
        has_divider = fragment.find("hr") is not None
        if has_text or has_divider:
            self._append_block(
                NormalizedBlock(
                    block_type="paragraph",
                    value=value,
                    kind=kind,
                )
            )

    def _append_block(self, block: NormalizedBlock) -> None:
        if len(self.blocks) >= MAX_IMPORTED_BLOCKS:
            self.discarded["block_limits"] += 1
            return
        self.blocks.append(block)

    @staticmethod
    def _contains_structural_block_descendant(node: Tag) -> bool:
        return any(
            isinstance(descendant, Tag)
            and descendant.name.lower() in STRUCTURAL_BLOCK_TAGS
            for descendant in node.descendants
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value.replace("\xa0", " "))

    @staticmethod
    def _is_safe_href(href: str) -> bool:
        if not href or any(ord(character) < 32 for character in href):
            return False
        try:
            parsed = urlsplit(href)
        except ValueError:
            return False
        return parsed.scheme.lower() in SAFE_LINK_SCHEMES

    @staticmethod
    def _semantic_inline_styles(style: str) -> tuple[bool, bool]:
        declarations = {}
        for item in style.split(";"):
            key, separator, value = item.partition(":")
            if separator:
                declarations[key.strip().lower()] = value.strip().lower()

        weight = declarations.get("font-weight", "")
        is_bold = weight in {"bold", "bolder"}
        if weight.isdigit():
            is_bold = int(weight) >= 600
        is_italic = declarations.get("font-style", "") in {"italic", "oblique"}
        return is_bold, is_italic

    @staticmethod
    def _positive_span(raw_value: object) -> int:
        try:
            return max(1, int(str(raw_value or "1")))
        except ValueError:
            return 1

    def _warnings(self) -> list[str]:
        warnings = []
        if self.discarded["images"]:
            warnings.append(
                self._quantity_message(
                    self.discarded["images"],
                    "Se descartó una imagen; agrégala manualmente desde el CMS.",
                    (
                        "Se descartaron {count} imágenes; agrégalas manualmente "
                        "desde el CMS."
                    ),
                )
            )
        if self.discarded["code"]:
            warnings.append(
                "El contenido con formato de código se convirtió a texto normal."
            )
        if self.discarded["nested_lists"]:
            warnings.append(
                "Las listas anidadas se aplanaron; revisa su orden antes de publicar."
            )
        if self.discarded["tracked_changes"]:
            warnings.append("Se eliminaron marcas de control de cambios del documento.")
        if self.discarded["unsafe_links"]:
            warnings.append(
                "Se quitaron destinos de enlace no seguros y se conservó su texto."
            )
        if self.discarded["unsafe_elements"]:
            warnings.append(
                "Se descartó contenido no compatible o potencialmente inseguro."
            )
        if self.discarded["unsupported_blocks"]:
            warnings.append(
                "Algunos elementos no compatibles se convirtieron a texto normal."
            )
        if self.discarded["complex_tables"]:
            warnings.append(
                "Las celdas combinadas o tablas anidadas se simplificaron; "
                "revisa la tabla antes de publicar."
            )
        if self.discarded["irregular_tables"]:
            warnings.append("Las filas irregulares se completaron con celdas vacías.")
        if self.discarded["table_limits"]:
            warnings.append(
                "Una tabla superó los límites de importación y se recortó de forma "
                "segura."
            )
        if self.discarded["empty_tables"]:
            warnings.append("Se descartó una tabla vacía.")
        if self.discarded["block_limits"]:
            warnings.append(
                f"Se importaron como máximo {MAX_IMPORTED_BLOCKS} bloques; "
                "el contenido adicional se descartó."
            )
        return warnings

    @staticmethod
    def _quantity_message(count: int, singular: str, plural: str) -> str:
        return singular if count == 1 else plural.format(count=count)


def normalize_plain_text(source: str) -> NormalizedPaste:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return NormalizedPaste(blocks=[], source="plain")

    blocks = []
    nonempty_lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in normalized.split("\n")
        if line.strip()
    ]
    for line in nonempty_lines[:MAX_IMPORTED_BLOCKS]:
        if not line:
            continue
        blocks.append(
            NormalizedBlock(
                block_type="paragraph",
                value=f"<p>{escape(line)}</p>",
                kind="paragraph",
            )
        )

    warnings = []
    if len(nonempty_lines) > MAX_IMPORTED_BLOCKS:
        warnings.append(
            f"Se importaron como máximo {MAX_IMPORTED_BLOCKS} bloques; "
            "el contenido adicional se descartó."
        )
    return NormalizedPaste(blocks=blocks, source="plain", warnings=warnings)


def normalize_paste(*, html_source: str = "", plain_text: str = "") -> NormalizedPaste:
    if html_source.strip():
        return HtmlPasteNormalizer().normalize(html_source)
    return normalize_plain_text(plain_text)
