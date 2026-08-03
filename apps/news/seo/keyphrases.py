import re
import unicodedata

from .content import normalize_whitespace


def normalize_for_match(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return normalize_whitespace(without_accents.casefold())


def normalize_slug_for_match(value: str) -> str:
    return normalize_for_match((value or "").replace("-", " ").replace("_", " "))


def contains_exact_phrase(value: str, phrase: str, *, slug: bool = False) -> bool:
    normalized_phrase = normalize_for_match(phrase)
    if not normalized_phrase:
        return False
    normalized_value = (
        normalize_slug_for_match(value) if slug else normalize_for_match(value)
    )
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)")
    return bool(pattern.search(normalized_value))


def count_exact_phrase(value: str, phrase: str) -> int:
    normalized_phrase = normalize_for_match(phrase)
    if not normalized_phrase:
        return 0
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)")
    return len(pattern.findall(normalize_for_match(value)))


def keyphrase_usage(value: str, phrase: str, word_count: int) -> tuple[int, float]:
    occurrences = count_exact_phrase(value, phrase)
    rate = occurrences / word_count * 100 if word_count else 0
    return occurrences, rate
