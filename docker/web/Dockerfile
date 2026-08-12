FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        gettext \
        libpq-dev \
        netcat-traditional \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" app \
    && useradd \
        --uid "${APP_UID}" \
        --gid "${APP_GID}" \
        --create-home \
        --home-dir /home/app \
        --shell /usr/sbin/nologin \
        app

COPY requirements.txt /app/requirements.txt
RUN pip install --require-hashes -r /app/requirements.txt \
    && python -c "import spacy; pipeline = spacy.load('es_core_news_sm', exclude=['ner']); required = {'tok2vec', 'morphologizer', 'parser', 'attribute_ruler', 'lemmatizer'}; missing = required.difference(pipeline.pipe_names); assert not missing, f'Missing spaCy components: {sorted(missing)}'; assert 'ner' not in pipeline.pipe_names; document = pipeline('Las investigaciones escolares avanzan. El equipo escribe.'); annotations = {'SENT_START', 'LEMMA', 'POS', 'MORPH', 'DEP'}; unavailable = {name for name in annotations if not document.has_annotation(name)}; assert not unavailable, f'Missing spaCy annotations: {sorted(unavailable)}'" \
    && python -c "import importlib.metadata as metadata; import pyphen; version = metadata.version('pyphen'); assert version == '0.17.2', version; language = pyphen.language_fallback('es_ES'); assert language == 'es', language; dictionary_path = pyphen.LANGUAGES[language]; assert dictionary_path.is_file(), dictionary_path; hyphenator = pyphen.Pyphen(lang='es_ES'); assert hyphenator.inserted('extraordinario') == 'ex-tra-or-di-na-rio'"

COPY docker/web/entrypoint.sh /usr/local/bin/school-newsroom-entrypoint
RUN chmod +x /usr/local/bin/school-newsroom-entrypoint

COPY --chown=app:app . /app
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app /home/app

EXPOSE 8000

ENTRYPOINT ["school-newsroom-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
