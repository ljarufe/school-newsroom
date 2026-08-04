# Third-Party Notices

School Newsroom uses the following separately licensed artifacts for local
Spanish linguistic analysis. The spaCy library license does not extend to the
Spanish model or its training datasets.

## spaCy

- Version: `3.8.14`
- Purpose: local NLP library and pipeline runtime
- Source: <https://github.com/explosion/spaCy>
- License: MIT

Copyright and license terms are provided by the upstream spaCy project in its
`LICENSE` file.

## es_core_news_sm

- Version: `3.8.0`
- Purpose: CPU-oriented Spanish linguistic pipeline
- Official source: <https://github.com/explosion/spacy-models/releases/tag/es_core_news_sm-3.8.0>
- Installed wheel: <https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl>
- Wheel SHA-256: `e451a83d6df79b87e9eed0cb553f03e99e36a3bab18a7b79f0dcfd1fdf875e12`
- spaCy compatibility: `>=3.8.0,<3.9.0`
- License: GNU General Public License v3.0

The model is a distinct distribution artifact. Project use of this GPL-3.0
model was explicitly accepted for School Newsroom. Its upstream package and
release contain the applicable license and model metadata.

## Click

- Version: `8.4.2`
- Purpose: direct compatibility workaround required because spaCy 3.8.14
  imports Click while the previously resolved project dependency graph did not
  install it
- Source: <https://github.com/pallets/click>
- License: BSD-3-Clause

Copyright and license terms are provided by the upstream Click project in its
`LICENSE.txt` file.
