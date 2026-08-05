# EPIC6-003 Stage A Feedback

## Stage A status

The approved public share actions are implemented, followed by a focused
correction from maintainer UAT. Automated correction validation is complete and
green. The known unrelated smart-paste browser warning from the original
implementation pass is retained below as historical evidence; it did not recur
in the correction pass.

## Maintainer UAT correction

Maintainer UAT found that the original script always revealed native share,
causing unsupported browsers to duplicate `Copiar enlace`; that inline status
looked like permanent article content; and that the generic heading treatment
was visually too close to article content.

The correction:

- renames the native action to `Compartir`;
- exposes it only when `navigator.share` exists and the exact payload passes
  `navigator.canShare` when that check exists;
- removes the native control from the usable DOM when support is absent,
  unshareable, or support detection throws, without copying, warning, or showing
  feedback during initialization;
- keeps `Copiar enlace` independent on every JavaScript-capable browser;
- replaces the inline status with one component-owned floating polite live
  notification and visible `Cerrar` control;
- auto-dismisses successful notifications after five seconds while keeping
  manual-copy failures visible until explicitly closed;
- clears prior timers, messages, and manual state whenever a notification is
  replaced or closed, so stale timers cannot hide newer feedback;
- gives the semantic `h2` a dedicated subtitle-style component treatment.

## Implementation structure and single source

- `build_public_metadata(page, request)` remains the single effective public
  metadata source and is called once by `NewsPage.get_context()`.
- Immutable `PublicShareLinks` and the pure `build_public_share_links()` builder
  derive every channel from `metadata.og_title`, `metadata.og_description`, and
  `metadata.canonical_url`.
- `NewsPage.get_context()` exposes the share structure only when the page is live
  and the Wagtail request is not a preview.
- The detail template owns the text-only component and loads one page-scoped
  progressive-enhancement script. No icon or other asset was downloaded.
- `static/public/js/share.js` owns Web Share support detection, Clipboard, the
  floating notification, shared readonly fallback, timer isolation, and safe
  local warning codes. It makes no requests, exposes no global application API,
  and logs no content.

## Channel and encoding contracts

- WhatsApp uses `https://wa.me/?text=` with the effective social title, a line
  break, and the effective canonical.
- X uses `https://x.com/intent/tweet` with separate `text` and `url` parameters.
- Facebook uses `https://www.facebook.com/sharer/sharer.php` with only the
  effective canonical in `u`.
- Email uses RFC-style `mailto:` percent encoding with the effective social
  title as subject and either the canonical alone or the effective social
  description, CRLF blank line, and canonical as body.
- Python standard-library URL encoding owns every external link. Django owns HTML
  escaping at the template boundary. The template and JavaScript build no
  external query strings.
- A configured external canonical remains external in every channel, native
  payload, Clipboard operation, readonly fallback, and no-JavaScript link.

## Public behavior

- One section appears after the article body and before tags in the required
  channel order. Its flex group wraps without changing DOM order or introducing
  a breakpoint, floating behavior, brand styling, or a secondary category.
- Normal live `noindex` news still shows the section. Real Wagtail preview
  requests do not expose the component or load its script.
- Without JavaScript, WhatsApp, X, Facebook, email, and the canonical noscript
  link remain available; native share and copy buttons stay hidden.
- Web Share receives `{title, text?, url}`. `AbortError` is silent. An absent,
  unshareable, or throwing support check removes `Compartir` without automatic
  copying or feedback. A technical rejection after an eligible interaction
  attempts to copy the canonical and reports one combined result.
- Clipboard writes only the effective canonical. Failure reveals and focuses a
  labelled readonly field containing only that canonical. Manual failure stays
  visible until closed; successful results auto-dismiss after five seconds.
- Accessible messages use the approved copy exactly:
  - `Enlace copiado.`
  - `No se pudo copiar automáticamente. Selecciona y copia este enlace.`
  - `No se pudo abrir el menú para compartir. Enlace copiado.`
  - `No se pudo abrir el menú para compartir. Selecciona y copia este enlace.`

## Privacy, security, and scope

- No model, schema, migration, Admin, panel, validation, permission, workflow,
  revision, social-image metadata, fallback, Open Graph, Twitter-X, or JSON-LD
  behavior changed.
- Eligibility and payload construction do not read or expose minor flags,
  sensitive-content state, internal contributors, or internal authorizations.
- No SDK, widget, iframe, tracker, cookie, telemetry, server call, server log,
  credential, secret, downloaded icon, or content-bearing warning was added.
- Local warnings contain only the stable component action and error name. Native
  cancellation produces no warning.

## Automated validation

- Focused correction Python suite during development: `4 passed`.
- Stable focused public Python suite: `47 passed`.
- Stable focused EPIC6-003 Playwright scenario: `1 passed (1.3s)`.
- `make migration-check`: passed with `No changes detected`.
- `make check`: passed with Ruff, migration detection, and `389 passed`.
- `make browser-test`: passed with `5 passed (13.5s)`.
- `git diff --check`: passed.

The original implementation pass completed `47` focused public Python tests,
`make migration-check`, `make check` with `389 passed`, and `git diff --check`.
Its focused public Playwright scenario passed in both corrected development
runs. During that earlier pass, the full browser gate remained red because the
pre-existing `smart-paste.spec.js` repeatedly failed at line 365: focusing its
first table cell left
`data-news-table-expanded="false"`. The rendered DOM showed the visible table
remained unselected after programmatic focus. That unrelated workflow was
inspected and was not changed under EPIC6-003. The failure did not recur in the
stable correction run, where all five browser scenarios passed.

The focused Python suite covers channel encoding, Unicode and adversarial
characters, description presence/absence, external canonical behavior,
noindex rendering, exact DOM order and attributes, no-JavaScript markup,
privacy exclusions, injection-resistant escaping, and the real Wagtail preview
pipeline. The focused browser scenario uses deterministic Web Share and
Clipboard mocks, inspects third-party hrefs without activating them, covers
success, cancellation, technical failures and manual fallback, and records page
errors.

## Manual validation and deferred UAT

Maintainer UAT produced the correction findings recorded above. Correction UAT
remains pending for compatible and incompatible Web Share browsers, transient
and manual notification behavior, narrow layout, and keyboard/focus behavior.
Tests do not navigate to external social platforms or claim completed posting.

Post-deploy UAT remains required for WhatsApp, X, and Facebook previews using a
public HTTPS URL. That UAT must verify the external compositor preview only; the
project cannot confirm that an external publication was completed.

## Warnings and known external limitations

- Web Share targets depend on the browser, operating system, and installed apps;
  the project does not promise a specific target or platform-specific action.
- `AbortError` cannot distinguish cancellation from no available share targets,
  and the approved behavior treats both silently.
- Clipboard depends on secure-context and browser permission behavior.
- Third-party composers and the user's mail handler are cross-origin and outside
  project control. The implementation guarantees only local href construction
  and activation contracts and cannot confirm completed publication.
- An out-of-scope smart-paste table-focus failure occurred repeatedly during the
  original implementation pass and is recorded in Automated validation. It did
  not recur in the stable correction run, and no smart-paste implementation or
  test was changed under EPIC6-003.
- No external platform contract change was observed during implementation. The
  preflight's recorded WhatsApp documentation extraction limitation and Meta
  documentation HTTP 429 remain the applicable research caveats; no research
  was repeated.

## New Work Discovered

`Audit and observability of public share integrations` remains a conditional
candidate with disposition `Trigger-based later`. Its triggers are a reported
real failure, approved future observability infrastructure, or an approved
scheduled audit. No Card, job, monitor, webhook, or alert was created.

Social-image metadata simplification is not recorded as future work.
