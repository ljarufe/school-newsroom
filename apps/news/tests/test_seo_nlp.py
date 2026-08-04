import pytest

from apps.news.seo import nlp


class FakeDocument:
    text = "Texto ficticio"

    def has_annotation(self, name):
        return True

    def __iter__(self):
        return iter(())


class FakePipeline:
    pipe_names = [
        "tok2vec",
        "morphologizer",
        "parser",
        "attribute_ruler",
        "lemmatizer",
    ]

    def __call__(self, value):
        return FakeDocument()

    def pipe(self, values):
        return (FakeDocument() for _value in values)


class FakeSpacy:
    def __init__(self, *, prefer_gpu=False, require_gpu_error=None):
        self.prefer_gpu_result = prefer_gpu
        self.require_gpu_error = require_gpu_error
        self.cpu_calls = 0
        self.prefer_calls = 0
        self.require_calls = 0
        self.load_calls = 0
        self.load_arguments = None

    def require_cpu(self):
        self.cpu_calls += 1

    def prefer_gpu(self):
        self.prefer_calls += 1
        return self.prefer_gpu_result

    def require_gpu(self):
        self.require_calls += 1
        if self.require_gpu_error:
            raise self.require_gpu_error

    def load(self, model, *, exclude):
        self.load_calls += 1
        self.load_arguments = (model, exclude)
        return FakePipeline()


@pytest.fixture(autouse=True)
def isolated_nlp_runtime():
    nlp.reset_runtime_cache()
    yield
    nlp.reset_runtime_cache()


@pytest.mark.parametrize(
    ("device", "prefer_gpu", "expected_active", "expected_calls"),
    [
        ("cpu", False, "cpu", (1, 0, 0)),
        ("prefer_gpu", False, "cpu", (0, 1, 0)),
        ("prefer_gpu", True, "gpu", (0, 1, 0)),
        ("require_gpu", False, "gpu", (0, 0, 1)),
    ],
)
def test_device_selection_precedes_single_lazy_load(
    monkeypatch,
    settings,
    device,
    prefer_gpu,
    expected_active,
    expected_calls,
) -> None:
    fake = FakeSpacy(prefer_gpu=prefer_gpu)
    settings.SEO_NLP_DEVICE = device
    monkeypatch.setattr(nlp.importlib, "import_module", lambda name: fake)

    first = nlp._load_pipeline()
    second = nlp._load_pipeline()

    assert first is second
    assert (fake.cpu_calls, fake.prefer_calls, fake.require_calls) == expected_calls
    assert fake.load_calls == 1
    assert fake.load_arguments == ("es_core_news_sm", ["ner"])
    assert nlp.runtime_info().active_device == expected_active
    assert nlp.runtime_info().load_attempts == 1


def test_require_gpu_failure_is_cached_without_retry(monkeypatch, settings) -> None:
    fake = FakeSpacy(require_gpu_error=RuntimeError("no gpu"))
    settings.SEO_NLP_DEVICE = "require_gpu"
    imports = []

    def fake_import(name):
        imports.append(name)
        return fake

    monkeypatch.setattr(nlp.importlib, "import_module", fake_import)

    with pytest.raises(nlp.NlpUnavailableError):
        nlp._load_pipeline()
    with pytest.raises(nlp.NlpUnavailableError):
        nlp._load_pipeline()

    assert imports == ["spacy"]
    assert fake.require_calls == 1
    assert fake.load_calls == 0
    assert nlp.runtime_info().load_attempts == 1


def test_inference_error_does_not_log_content_or_discard_loaded_pipeline(
    monkeypatch,
    caplog,
) -> None:
    sensitive_fixture = "contenido editorial completo que no debe registrarse"

    class BrokenPipeline(FakePipeline):
        def pipe(self, values):
            raise ValueError("bounded technical failure")

    pipeline = BrokenPipeline()
    monkeypatch.setattr(nlp, "_PIPELINE", pipeline)
    monkeypatch.setattr(nlp, "_LOAD_ATTEMPTED", True)
    monkeypatch.setattr(nlp, "_LOAD_ERROR", False)

    with pytest.raises(nlp.NlpInferenceError):
        nlp.analyze_texts([sensitive_fixture])

    assert nlp._PIPELINE is pipeline
    assert not nlp._LOAD_ERROR
    assert sensitive_fixture not in caplog.text
    assert "bounded technical failure" not in caplog.text


def test_pipeline_rejects_missing_required_components(monkeypatch) -> None:
    fake = FakeSpacy()
    broken = FakePipeline()
    broken.pipe_names = ["tok2vec", "lemmatizer"]
    fake.load = lambda model, exclude: broken
    monkeypatch.setattr(nlp.importlib, "import_module", lambda name: fake)

    with pytest.raises(nlp.NlpUnavailableError):
        nlp._load_pipeline()

    assert nlp.runtime_info().load_attempts == 1
