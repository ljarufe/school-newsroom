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

## openpyxl

- Version: `3.1.5`
- Purpose: direct XLSX reader for the reviewed INEI UBIGEO updater
- Source: <https://foss.heptapod.net/openpyxl/openpyxl>
- Documentation: <https://openpyxl.readthedocs.io/en/stable/>
- License: MIT

Version and license were inspected from the resolved installed distribution.
The dependency reads controlled local files and the single project-owned official
INEI resource; it is not used on request, startup, migration, or deploy paths.

## Pyphen

- Version: `0.17.2`
- Purpose: local syllable counting for the Flesch-Szigriszt index
- Source: <https://github.com/Kozea/Pyphen/tree/0.17.2>
- Installed wheel: `pyphen-0.17.2-py3-none-any.whl`
- Wheel SHA-256: `3a07fb017cb2341e1d9ff31b8634efb1ae4dc4b130468c7c39dd3d32e7c3affd`
- Declared license alternatives: GPL-2.0-or-later / LGPL-2.1-or-later /
  MPL-1.1
- Effective license selected by School Newsroom: MPL-1.1

The installed distribution includes `COPYING.GPL`, `COPYING.LGPL`, and
`COPYING.MPL`. Pyphen states that its bundled dictionaries come from the
LibreOffice dictionaries repository and may have their own licenses; the
library license is therefore not attributed automatically to a dictionary.

## Spanish hyphenation dictionary bundled with Pyphen

- Purpose: offline syllable boundaries requested through `Pyphen(lang="es_ES")`
- Installed dictionary: `pyphen/dictionaries/hyph_es.dic`
- Runtime resolution: `es_ES` falls back to Pyphen's bundled generic `es`
  dictionary
- Dictionary SHA-256: `b2e170c3c25f5de25447ca0acf6bc8baf9dd761e228e9646e2c25f2e7c47f4f6`
- Source identified by the bundled notice: Spanish hyphenation patterns from
  LibreOffice/Apache OpenOffice
- Initial author identified by the bundled notice: Santiago Bosio
- Declared license alternatives: GPL-3.0-or-later / LGPL-3.0-or-later /
  MPL-1.1-or-later
- Effective license selected by School Newsroom: MPL-1.1

The exact contents of
`pyphen/dictionaries/README_hyph_es.txt` bundled in the inspected Pyphen
0.17.2 wheel are reproduced below:

```text
  ****************************************************************************
  **                                                                        **
  **              Patrones de separación silábica en español de             **
  **                      LibreOffice/Apache OpenOffice                     **
  **                                                                        **
  ****************************************************************************
  **  VERSIÓN GENÉRICA PARA TODAS LAS LOCALIZACIONES DEL ESPAÑOL            **
  ****************************************************************************

                                 Versión __VERSION__

SUMARIO

1. AUTOR
2. LICENCIA
3. COLABORACIÓN
4. AGRADECIMIENTOS


1. AUTOR

   Este fichero de patrones para separación silábica ha sido desarrollado
inicialmente por Santiago Bosio; mediante el uso de la herramienta libre
"patgen" y datos de entrenamiento etiquetados manualmente.

2. LICENCIA

   Este listado de patrones para separación silábica, integrado por el
fichero hyph_es_ANY.dic se distribuye bajo un triple esquema de licencias
disjuntas: GNU GPL versión 3 o posterior, GNU LGPL versión 3 o posterior, ó
MPL versión 1.1 o posterior.  Puede seleccionar libremente bajo cuál de
estas licencias utilizará este diccionario.  En el fichero LICENSE.md
encontrá más detalles.

3. COLABORACIÓN

   Este diccionario es resultado del trabajo colaborativo de muchas personas.
La buena noticia es que ¡usted también puede participar!

   ¿Tiene dudas o sugerencias? ¿Desearía ver palabras agregadas, o que se
realizaran correcciones? Consulte las indicaciones técnicas publicadas en
CONTRIBUTING.md. Estaremos encantados de atenderle.
```

The bundled wheel does not contain the `LICENSE.md` referenced by that notice
and does not contain an MIT-origin attribution for this Spanish dictionary.
The current LibreOffice Spanish dictionary license may be consulted separately
at <https://github.com/LibreOffice/dictionaries/blob/master/es/LICENSE.md> as
external upstream provenance. It is not represented here as content bundled
in Pyphen 0.17.2.

## caddy-ratelimit

- Version: `v0.1.0`
- Purpose: per-network-peer HTTP rate limiting in the staging Caddy proxy
- Source: <https://github.com/mholt/caddy-ratelimit/tree/v0.1.0>
- License: Apache License 2.0

The module is compiled into the custom Caddy 2.11.4 staging image. It is not an
official module of the Caddy Web Server organization.

## Fail2ban

- Supported host version: Ubuntu Noble package `1.0.2-3ubuntu0.1` (Fail2ban
  `1.0.x` configuration contract)
- Purpose: temporary host-level escalation after repeated Caddy 429 responses
- Source: <https://github.com/fail2ban/fail2ban/tree/1.0.2>
- License: GNU General Public License v2.0

Fail2ban is an explicit host prerequisite. It is not installed in an
application container or by normal application startup.
