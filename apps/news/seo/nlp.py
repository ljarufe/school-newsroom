import importlib
import logging
import threading
from collections.abc import Iterable
from dataclasses import dataclass

from django.conf import settings

from .keyphrases import normalize_for_match

logger = logging.getLogger(__name__)

REQUIRED_COMPONENTS = frozenset(
    {
        "tok2vec",
        "morphologizer",
        "parser",
        "attribute_ruler",
        "lemmatizer",
    }
)
CONTENT_POS = frozenset({"ADJ", "ADV", "NOUN", "PROPN", "VERB"})


class NlpUnavailableError(RuntimeError):
    """The configured local linguistic pipeline could not be loaded."""


class NlpInferenceError(RuntimeError):
    """The loaded local pipeline failed for the current inference."""


@dataclass(frozen=True)
class NlpToken:
    text: str
    lemma: str
    normalized_text: str
    normalized_lemma: str
    start: int
    end: int
    pos: str
    significant: bool
    content: bool


@dataclass(frozen=True)
class AnalyzedText:
    text: str
    tokens: tuple[NlpToken, ...]


@dataclass(frozen=True)
class NlpRuntimeInfo:
    model: str
    configured_device: str
    active_device: str
    components: tuple[str, ...]
    load_attempts: int


_LOCK = threading.Lock()
_PIPELINE = None
_LOAD_ATTEMPTED = False
_LOAD_ERROR = False
_LOAD_ATTEMPTS = 0
_ACTIVE_DEVICE = ""
_ACTIVE_COMPONENTS: tuple[str, ...] = ()


def _select_device(spacy_module, configured_device: str) -> str:
    if configured_device == "cpu":
        spacy_module.require_cpu()
        return "cpu"
    if configured_device == "prefer_gpu":
        return "gpu" if spacy_module.prefer_gpu() else "cpu"
    spacy_module.require_gpu()
    return "gpu"


def _load_pipeline():
    global _ACTIVE_COMPONENTS
    global _ACTIVE_DEVICE
    global _LOAD_ATTEMPTED
    global _LOAD_ATTEMPTS
    global _LOAD_ERROR
    global _PIPELINE

    if _LOAD_ATTEMPTED:
        if _LOAD_ERROR:
            raise NlpUnavailableError from None
        return _PIPELINE

    with _LOCK:
        if _LOAD_ATTEMPTED:
            if _LOAD_ERROR:
                raise NlpUnavailableError from None
            return _PIPELINE

        _LOAD_ATTEMPTED = True
        _LOAD_ATTEMPTS += 1
        model = settings.SEO_NLP_MODEL
        device = settings.SEO_NLP_DEVICE
        try:
            spacy_module = importlib.import_module("spacy")
            active_device = _select_device(spacy_module, device)
            pipeline = spacy_module.load(model, exclude=["ner"])
            components = tuple(pipeline.pipe_names)
            missing = REQUIRED_COMPONENTS.difference(components)
            if missing or "ner" in components:
                raise RuntimeError(
                    "The configured pipeline does not provide the required components."
                )
            smoke_doc = pipeline(
                "Las investigaciones escolares avanzan. El equipo escribe."
            )
            required_annotations = {"SENT_START", "LEMMA", "POS", "MORPH", "DEP"}
            if any(
                not smoke_doc.has_annotation(annotation)
                for annotation in required_annotations
            ):
                raise RuntimeError(
                    "The configured pipeline does not provide the required annotations."
                )
        except Exception as error:
            _LOAD_ERROR = True
            logger.error(
                "SEO linguistic pipeline load failed (model=%s, error=%s).",
                model,
                type(error).__name__,
            )
            raise NlpUnavailableError from None

        _PIPELINE = pipeline
        _ACTIVE_DEVICE = active_device
        _ACTIVE_COMPONENTS = components
        return _PIPELINE


def _convert_doc(doc) -> AnalyzedText:
    tokens = tuple(
        NlpToken(
            text=token.text,
            lemma=token.lemma_,
            normalized_text=normalize_for_match(token.text),
            normalized_lemma=normalize_for_match(token.lemma_ or token.text),
            start=token.idx,
            end=token.idx + len(token.text),
            pos=token.pos_,
            significant=not token.is_space and not token.is_punct,
            content=token.pos_ in CONTENT_POS,
        )
        for token in doc
    )
    return AnalyzedText(text=doc.text, tokens=tokens)


def analyze_texts(texts: Iterable[str]) -> tuple[AnalyzedText, ...]:
    pipeline = _load_pipeline()
    values = tuple(texts)
    try:
        docs = pipeline.pipe(values)
        return tuple(_convert_doc(doc) for doc in docs)
    except Exception as error:
        logger.error(
            "SEO linguistic inference failed (error=%s).",
            type(error).__name__,
        )
        raise NlpInferenceError from None


def runtime_info() -> NlpRuntimeInfo:
    return NlpRuntimeInfo(
        model=settings.SEO_NLP_MODEL,
        configured_device=settings.SEO_NLP_DEVICE,
        active_device=_ACTIVE_DEVICE,
        components=_ACTIVE_COMPONENTS,
        load_attempts=_LOAD_ATTEMPTS,
    )


def reset_runtime_cache() -> None:
    """Reset process state for isolated tests; application code never retries."""

    global _ACTIVE_COMPONENTS
    global _ACTIVE_DEVICE
    global _LOAD_ATTEMPTED
    global _LOAD_ATTEMPTS
    global _LOAD_ERROR
    global _PIPELINE

    with _LOCK:
        _PIPELINE = None
        _LOAD_ATTEMPTED = False
        _LOAD_ERROR = False
        _LOAD_ATTEMPTS = 0
        _ACTIVE_DEVICE = ""
        _ACTIVE_COMPONENTS = ()
