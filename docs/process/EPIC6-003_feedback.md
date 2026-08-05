# EPIC6-003 Closing Feedback Final

## Final status

EPIC6-003 is technically and operationally stable and ready for squash merge.

The approved public sharing actions were implemented, reviewed through the
complete relevant diff, corrected after maintainer UAT, and revalidated. The
final correction UAT passed. The final automated gates passed, pull request CI
completed successfully on the final implementation state, and automated review
completed without findings.

This ticket introduces no model or schema changes and no migrations.

## Delivered outcome

Public live news detail pages now expose one text-only sharing section after the
article body and before the tags.

The component uses the existing effective public metadata as its single source:

- social title from `PublicMetadata.og_title`;
- social description from `PublicMetadata.og_description`;
- effective canonical from `PublicMetadata.canonical_url`.

The implementation provides:

- conditional native Web Share through `Compartir`;
- WhatsApp;
- X;
- Facebook;
- email;
- Clipboard through `Copiar enlace`;
- a no-JavaScript canonical fallback;
- a floating, closable, accessible notification;
- a persistent readonly manual-copy fallback when Clipboard cannot write.

## Implementation structure

- `build_public_metadata(page, request)` remains the single effective public
  metadata source and is called once by `NewsPage.get_context()`.
- Immutable `PublicShareLinks` and the pure `build_public_share_links()` builder
  derive every external share link from the effective social metadata and
  canonical.
- `NewsPage.get_context()` exposes the share structure only for live,
  non-preview requests.
- `templates/news/news_page.html` renders the component after the article body
  and before tags, and loads one page-scoped progressive-enhancement script.
- `static/public/js/share.js` owns Web Share capability detection, Clipboard,
  notification state, manual fallback, timer isolation, and safe local warning
  codes.
- `static/public/css/site.css` owns the component, subtitle, responsive action
  group, notification, close control, and manual field presentation.
- The existing isolated browser fixture and workflow path filters were extended
  without adding a new runner, framework, build system, or dependency.

## Channel and encoding contracts

- WhatsApp uses `https://wa.me/?text=` with the effective social title, one line
  break, and the effective canonical.
- X uses `https://x.com/intent/tweet` with separate `text` and `url` parameters.
- Facebook uses `https://www.facebook.com/sharer/sharer.php` with only the
  effective canonical in `u`.
- Email uses RFC-style `mailto:` percent encoding with:
  - effective social title as subject;
  - effective social description, one CRLF blank line, and canonical as body;
  - canonical alone when the description is empty.
- Python standard-library URL encoding owns every external URL.
- Django owns HTML escaping at the template boundary.
- Templates and JavaScript do not rebuild external query strings.
- A configured external canonical remains external in every channel, native
  payload, Clipboard operation, readonly fallback, and no-JavaScript link.

## Final public behavior

### Native Web Share

The native action is labelled exactly `Compartir`.

It is exposed only when:

- `navigator.share` exists; and
- `navigator.canShare` is absent or accepts the exact payload.

When Web Share is absent, unshareable, or capability detection throws:

- `Compartir` is removed from the usable DOM;
- no automatic copy occurs;
- no warning or user-facing notification appears;
- `Copiar enlace` and the server-generated actions remain available.

The native payload contains:

- `title`;
- optional `text`;
- `url`.

`AbortError` is treated as silent cancellation with no warning, notification,
or Clipboard fallback.

A different native-share failure logs only the stable action and error name,
then attempts to copy the canonical and reports one combined result.

### Clipboard and notifications

Clipboard writes only the effective canonical.

Successful feedback:

- appears in one floating polite notification;
- includes a visible `Cerrar` control;
- does not move focus;
- dismisses automatically after five seconds;
- can be dismissed manually.

Manual-copy failure:

- remains visible until explicitly closed;
- contains a labelled readonly field;
- focuses and selects the effective canonical when supported;
- is reset when the notification is closed or replaced.

Notification replacement clears earlier state and timers. An older timer cannot
hide a newer notification.

Approved final messages are:

- `Enlace copiado.`
- `No se pudo copiar automáticamente. Selecciona y copia este enlace.`
- `No se pudo abrir el menú para compartir. Enlace copiado.`
- `No se pudo abrir el menú para compartir. Selecciona y copia este enlace.`

### Presentation and progressive enhancement

- `Compartir esta noticia` remains a semantic `h2`.
- It has a dedicated subtitle treatment distinct from article-body prose.
- Actions wrap responsively without changing DOM order.
- No icon, logo, floating share bar, brand styling, SDK, widget, or iframe was
  added.
- Without JavaScript, WhatsApp, X, Facebook, email, and the canonical fallback
  remain usable.
- `Compartir` and `Copiar enlace` remain hidden without JavaScript.
- Normal live `noindex` news still shows the component.
- Real Wagtail preview requests do not expose the component or load its script.

## Maintainer UAT

Initial maintainer UAT confirmed that the server-generated WhatsApp and X
composer links received the expected title and URL, and identified three
usability findings:

1. unsupported desktop browsers exposed a native action that duplicated
   `Copiar enlace`;
2. action feedback looked like permanent article content;
3. the generic heading treatment looked too similar to article-body content.

The focused correction:

- renamed the native action to `Compartir`;
- made it capability-dependent;
- removed unsupported native controls without side effects;
- replaced inline feedback with the floating notification;
- added deterministic dismissal and stale-timer protection;
- added persistent manual-copy fallback behavior;
- added dedicated subtitle styling.

Correction UAT passed for:

- a desktop browser without Web Share;
- Clipboard success;
- blocked Clipboard permission and manual fallback;
- automatic and manual notification dismissal;
- responsive narrow layout;
- keyboard activation and visible focus;
- Android native Web Share through a local ADB port reverse;
- silent native-selector cancellation.

No remaining local UAT finding blocks closure.

## Automated validation

Final stable evidence:

- focused public Python suites: `47 passed`;
- focused EPIC6-003 Playwright scenario: `1 passed (1.3s)`;
- `make migration-check`: passed with `No changes detected`;
- `make check`: passed with Ruff, migration detection, and `389 passed`;
- `make browser-test`: passed with `5 passed (13.5s)`;
- `git diff --check`: passed.

The focused Python suite covers:

- channel encoding;
- Unicode and adversarial characters;
- description presence and absence;
- external canonical behavior;
- noindex rendering;
- exact DOM order and attributes;
- no-JavaScript markup;
- privacy exclusions;
- injection-resistant escaping;
- the real Wagtail preview pipeline.

The focused browser scenario covers:

- supported Web Share and the exact payload;
- missing Web Share;
- unshareable payload;
- throwing capability detection;
- silent `AbortError`;
- technical native failure;
- successful and failed Clipboard writes;
- exact notification messages;
- deterministic five-second dismissal;
- manual close;
- persistent manual fallback;
- stale-timer isolation;
- keyboard and focus behavior;
- narrow viewport overflow;
- zero page errors;
- no third-party navigation.

During the original implementation pass, the pre-existing smart-paste browser
scenario intermittently failed at its table-focus assertion. No smart-paste
implementation or test was changed under EPIC6-003. The failure did not recur
in the final correction run, where all five browser scenarios passed.

## Pull request and review evidence

- The feature branch was committed and pushed through the repository's normal
  Git entry points.
- Pull request CI completed successfully on the final implementation state.
- Automated pull request review completed without findings.
- No material post-review implementation delta invalidated the final evidence.
- The complete relevant diff was reviewed once, then the focused correction
  delta was reviewed after UAT findings were addressed.

## Privacy, security, and scope

The implementation does not read or expose:

- minor-identification flags;
- publication-authorization state;
- sensitive-content state;
- internal contributors;
- internal authorizations.

The ticket adds no:

- SDK;
- tracker;
- analytics;
- pixel;
- cookie;
- telemetry;
- server call;
- server log;
- credential;
- secret;
- downloaded icon;
- content-bearing console warning.

Local warnings contain only the stable component action and error name. Native
cancellation produces no warning.

No changes were made to:

- model fields;
- schema;
- migrations;
- Admin panels;
- form validation;
- permissions;
- workflow;
- revisions;
- social-image metadata;
- social-image caption, alt, or credit;
- image fallback order;
- Open Graph;
- Twitter-X metadata;
- JSON-LD.

## Accepted deferred deployment validation

Rich-link previews for WhatsApp, X, and Facebook were not considered validly
testable against `localhost`, because external crawlers cannot retrieve a local
page or its social image.

The deferral is accepted and does not block EPIC6-003 because this ticket's local
contracts are fully covered:

- correct server-generated URLs;
- correct effective canonical;
- correct public social metadata preservation;
- correct local activation behavior;
- no third-party navigation in automated tests.

A future deployment or automatic-deployment ticket must include UAT using a
publicly reachable HTTPS news URL with a public social image and verify:

- WhatsApp link preview;
- X post/card behavior after publication or through the then-current validation
  mechanism;
- Facebook crawler recognition and share preview;
- cache/refetch behavior where the platform exposes it.

The project still cannot guarantee that an external platform creates a preview
or that a user completes a publication.

## External limitations

- Web Share targets depend on browser, operating system, and installed apps.
- The project does not promise a particular native target or a direct
  platform-specific action.
- `AbortError` cannot distinguish cancellation from no available share targets;
  the approved behavior treats both silently.
- Clipboard depends on secure-context and browser-permission behavior.
- The user's operating system or browser chooses the `mailto:` handler.
- External composers, crawlers, caches, and final publication are outside the
  application's control.
- The preflight's WhatsApp documentation-extraction limitation and Meta
  documentation HTTP 429 remain recorded research limitations; no speculative
  SDK or alternate contract was introduced.

## Files changed

- `.github/workflows/browser-regression.yml`
- `apps/news/management/commands/setup_browser_test.py`
- `apps/news/models.py`
- `apps/news/seo_metadata.py`
- `apps/news/tests/test_public_share.py`
- `docker-compose.browser.yml`
- `docs/editorial/guia_de_uso.md`
- `docs/process/EPIC6-003_feedback.md`
- `static/public/css/site.css`
- `static/public/js/share.js`
- `templates/news/news_page.html`
- `tests/browser/public-share.spec.js`

## New Work Discovered

### Audit and observability of public share integrations

Disposition: `Trigger-based later`.

Possible triggers:

- a reported real-world integration failure;
- approved future observability infrastructure;
- an approved scheduled external-contract audit.

No Card, job, monitor, webhook, alert, or automation was created.

Social-image metadata simplification is not recorded as future work.

## Durable process finding — agentic token consumption

The maintainer reported that the EPIC6-003 workflow consumed more than 80% of
the weekly plan allowance within a few hours and left approximately 9%
available. This consumption level is not sustainable for a mostly personal,
non-profit project and cannot be solved by moving to a more expensive plan.

This is a material execution-process finding, not a product defect.

The implementation workflow should be revised durably in F009:

1. The development chat receives the original ticket and performs the complete
   repository inspection, primary-source research, contradiction analysis, and
   technical decision closure.
2. The development chat asks the maintainer only the unresolved material product,
   privacy, data, architecture, or UAT questions.
3. Codex receives:
   - the original ticket unchanged;
   - a compact implementation brief containing only closed contracts, expected
     files, risks, prohibitions, tests, and hard-stop conditions;
   - a short execution prompt.
4. Codex does not repeat completed external research or produce a second broad
   preflight.
5. Model selection must be proportional:
   - Luna for mechanical, documentation, formatting, and very small test fixes;
   - Terra as the default for a technically closed normal ticket;
   - Terra High for a closed but genuinely cross-layer feature;
   - Sol only for materially unresolved architecture, security, privacy,
     migration, or repeated-failure work.
6. Fast, Max, and Ultra remain disabled by default and require an explicit,
   ticket-specific justification.
7. Every Codex prompt still declares model, reasoning, speed, and motive.
8. The complete research record remains in the development chat; Codex receives
   only the compact actionable projection.
9. Correction prompts contain only the observed defect, approved behavior,
   affected boundary, required evidence, and exclusions.
10. Usage should be recorded before and after each Codex execution until a
    sustainable per-ticket baseline is established.
11. A weekly reserve must be protected for review findings and unavoidable
    corrections.
12. The final ticket handoff remains a single delivery after operational closure.

Recommended provisional size controls:

- implementation brief: approximately 1,000–1,500 words;
- kickoff prompt: approximately 400–800 words;
- focused correction prompt: approximately 250–600 words.

Recommended provisional usage controls:

- normal ticket target: no more than approximately 8% of weekly capacity;
- complex ticket target: no more than approximately 12%;
- pause and reassess at approximately 15%;
- preserve at least approximately 25% of weekly capacity for review,
  corrections, and blocking work.

These percentages are initial operating limits and should be recalibrated after
two or three tickets using recorded consumption rather than treated as permanent
product requirements.

## Durable knowledge candidates

1. Public share links are derived exclusively from effective public social
   metadata and canonical.
2. Native Web Share is capability-dependent and never substitutes itself with
   automatic copying when unsupported.
3. Clipboard feedback uses one transient notification; manual fallback remains
   until closed.
4. Public share actions appear on live `noindex` news but not in Wagtail preview.
5. Rich social previews require post-deploy UAT against a public HTTPS URL.
6. F009 needs a durable token-budget and model-routing revision before the next
   substantial Codex implementation workflow.

## Closing disposition

EPIC6-003 satisfies its approved local implementation, accessibility, privacy,
testing, documentation, UAT, CI, and review requirements.

The accepted post-deploy rich-preview validation is explicitly assigned to a
future deployment-related ticket and does not block merge.

The branch is ready for its final documentation commit, squash merge, local
synchronization, branch cleanup, and Planka transition from `Review` to `Done`.
It must not move to `Released` until the functionality is deployed and verified
in a real environment.
