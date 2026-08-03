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
