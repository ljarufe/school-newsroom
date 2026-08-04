import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from wagtail.rich_text import RichText

WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class LinkInfo:
    href: str
    linktype: str = ""


@dataclass(frozen=True)
class ContentEvent:
    kind: str
    text: str


@dataclass(frozen=True)
class ContentSegment:
    kind: str
    order: int
    text: str
    reference: str


@dataclass
class ContentSnapshot:
    text: str = ""
    paragraphs: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    body_image_alts: list[str] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)
    events: list[ContentEvent] = field(default_factory=list)
    segments: list[ContentSegment] = field(default_factory=list)

    @property
    def introduction(self) -> str:
        return self.paragraphs[0] if self.paragraphs else ""

    @property
    def word_count(self) -> int:
        return count_words(self.text)


class _RichTextExtractor(HTMLParser):
    captured_tags = {"p": "paragraph", "li": "list", "blockquote": "quote"}
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
                self.events.append(ContentEvent(self.captured_tags[tag], text))
            return

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self._captures:
            self._captures[-1][1].append(data)


def normalize_whitespace(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip()


def count_words(value: str) -> int:
    return len(WORD_RE.findall(value or ""))


def extract_content(body) -> ContentSnapshot:
    snapshot = ContentSnapshot()
    text_parts: list[str] = []

    if not body:
        return snapshot

    for block_index, child in enumerate(body):
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
            for event_index, event in enumerate(parser.events):
                snapshot.segments.append(
                    ContentSegment(
                        kind=event.kind,
                        order=len(snapshot.segments),
                        text=event.text,
                        reference=f"body:{block_index}:{event_index}",
                    )
                )
            if visible_text and not parser.events:
                snapshot.paragraphs.append(visible_text)
                snapshot.events.append(ContentEvent("paragraph", visible_text))
                snapshot.segments.append(
                    ContentSegment(
                        kind="paragraph",
                        order=len(snapshot.segments),
                        text=visible_text,
                        reference=f"body:{block_index}:0",
                    )
                )
        elif child.block_type == "article_image":
            alt_text = normalize_whitespace(str(child.value.get("alt_text") or ""))
            snapshot.body_image_alts.append(alt_text)
            if alt_text:
                snapshot.segments.append(
                    ContentSegment(
                        kind="image_alt",
                        order=len(snapshot.segments),
                        text=alt_text,
                        reference=f"body:{block_index}:alt",
                    )
                )
        elif child.block_type == "table":
            value = child.value or {}
            caption = normalize_whitespace(str(value.get("table_caption") or ""))
            table_rows = value.get("data") or []
            visible_rows = [
                normalize_whitespace(
                    " ".join("" if cell is None else str(cell) for cell in row)
                )
                for row in table_rows
                if isinstance(row, list)
            ]
            table_text = normalize_whitespace(
                " ".join([caption, *(row for row in visible_rows if row)])
            )
            if table_text:
                snapshot.segments.append(
                    ContentSegment(
                        kind="table",
                        order=len(snapshot.segments),
                        text=table_text,
                        reference=f"body:{block_index}:table",
                    )
                )

    snapshot.text = normalize_whitespace(" ".join(text_parts))
    return snapshot


def build_page_segments(page, snapshot: ContentSnapshot) -> tuple[ContentSegment, ...]:
    """Return stable, visible analysis segments without reparsing StreamField."""

    segments: list[ContentSegment] = []

    def add(kind: str, value: str, reference: str) -> None:
        text = normalize_whitespace(value or "")
        if not text:
            return
        segments.append(
            ContentSegment(
                kind=kind,
                order=len(segments),
                text=text,
                reference=reference,
            )
        )

    public_title = str(getattr(page, "title", "") or "")
    effective_seo_title = str(getattr(page, "seo_title", "") or "").strip()
    effective_seo_title = effective_seo_title or public_title
    add("public_title", public_title, "page:title")
    if normalize_whitespace(effective_seo_title) != normalize_whitespace(public_title):
        add("seo_title", effective_seo_title, "page:seo_title")
    add(
        "description",
        str(getattr(page, "search_description", "") or ""),
        "page:search_description",
    )
    add(
        "image_alt",
        str(getattr(page, "featured_image_alt_text", "") or ""),
        "page:featured_image_alt_text",
    )
    for body_segment in snapshot.segments:
        segments.append(
            ContentSegment(
                kind=body_segment.kind,
                order=len(segments),
                text=body_segment.text,
                reference=body_segment.reference,
            )
        )
    return tuple(segments)
