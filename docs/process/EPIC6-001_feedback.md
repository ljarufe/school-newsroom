# EPIC6-001 Feedback

## Status

Closing Feedback Final

## Implementation summary

EPIC6-001 delivers a navigable, responsive public vertical slice without adding demo content or a separate frontend build. Home, the public news list, news detail, and institutional pages share one public base layout with Spanish landmarks, keyboard-visible focus, a skip link, responsive navigation, and a common footer.

Bootstrap 5.3.3 is loaded centrally from jsDelivr with Subresource Integrity and `crossorigin="anonymous"`. Project styling is isolated in `static/public/css/site.css`. The Bootstrap imports and this stylesheet form the replaceable provisional visual layer; no Node, React, Next.js, Tailwind, or asset-build dependency was introduced.

Home and the public news list share `public_news_pages()`, which applies `live().public()`, selects section, school, and featured image, prefetches only ordered public credits, and orders by `-publication_date` then `-first_published_at`. Home evaluates at most 12 records, assigns the first to `featured_news`, and assigns the remaining records to `secondary_news`, so the featured story cannot be duplicated. Both surfaces render explicit empty states and never manufacture cards or content.

The public list route is `/noticias/`. Its filter contract is `?seccion=<NewsSection.slug>`. No filter lists all public news; a valid section filters the same public query; a valid section without results renders a section-specific empty state; and an unknown slug returns HTTP 200 with a safe, clear error state and a link back to the complete list.

Public navigation is prepared from real `NewsSection` records and direct institutional children of the current site Home that are live, public, and marked `show_in_menus`. Missing, draft, restricted, or menu-disabled institutional pages do not create placeholders. Sections link to the list filter; no Wagtail section pages were added.

News detail keeps the existing canonical, robots, Open Graph, Twitter/X, and safe JSON-LD blocks. Existing public fields, ordered public credits, featured image, structured body, article-image alt/caption/optional credit, YouTube/Spotify output and fallbacks, and tags remain present. No public query or template loads internal contributor relations, and no internal minor name, age band, or privacy flag is rendered.

The final UAT also produced two small visual refinements:

- additional top spacing before the Home `Últimas noticias` section;
- responsive 16:9 sizing for article-body iframes so YouTube embeds preserve a normal video proportion.

## Files changed

- `apps/home/models.py`: Home page context split, sitemap behavior, and `InstitutionalPage`.
- `apps/home/migrations/0003_institutionalpage.py`: generated schema migration, later adjusted to depend on a Wagtail migration available across the project's declared Wagtail 7 support range.
- `apps/home/templatetags/__init__.py`: template-tag package.
- `apps/home/templatetags/public_navigation.py`: real-content public navigation.
- `apps/home/tests.py`: institutional tree, rendering, labels, rich-text features, menu visibility, and environment noindex/sitemap regression tests.
- `apps/news/selectors.py`: shared public-news query and editorial ordering.
- `apps/news/views.py`: public list view and section-filter behavior.
- `apps/news/tests/test_public_rendering.py`: Home split, list filtering, visibility/privacy, empty states, and shared-layout tests.
- `config/urls.py`: named `/noticias/` route before Wagtail's catch-all.
- `templates/base.html`: common public document, Bootstrap integration, landmarks, footer, and extensible blocks.
- `templates/includes/public_navigation.html`: responsive public navigation.
- `templates/includes/news_card.html`: shared Home/list news card.
- `templates/home/home_page.html`: editorial Home hero, secondary cards, empty state, and final spacing adjustment.
- `templates/home/institutional_page.html`: common-layout institutional page.
- `templates/news/news_list.html`: public list/filter and safe empty states.
- `templates/news/news_page.html`: common-layout visual detail preserving SEO.
- `templates/news/blocks/article_image.html`: responsive article-image classes.
- `static/public/css/site.css`: isolated provisional editorial styling, including responsive article iframe sizing.
- `docs/editorial/guia_de_uso.md`: public navigation, institutional authoring, real-content verification, and current limitations.
- `docs/process/EPIC6-001_feedback.md`: this final Stage B closure record.

## Migration details

`apps/home/migrations/0003_institutionalpage.py` creates only the new `InstitutionalPage` model. It contains no `RunPython`, data migration, automatic page creation, or content creation.

The migration was originally generated under the resolved Wagtail 7.4.2 environment with a dependency on:

```text
wagtailcore.0097_baselogentry_uuid_action_timestamp_indexes
```

PR review identified that this node is newer than the lower bound permitted by the project's declared Wagtail range (`>=7.0,<8.0`). The dependency was corrected to:

```text
wagtailcore.0094_alter_page_locale
```

This preserves the intended page-model dependency while keeping the migration graph compatible with the supported Wagtail 7 range. The migration operations and schema outcome were not otherwise changed.

The migration also depends on:

```text
home.0002_alter_homepage_options
```

The maintainer applied the migration successfully to the local persistent development database before browser UAT.

## Automated validation

Initial focused public, institutional, SEO, body-image, and provider behavior:

```text
56 passed
```

Focused public/institutional delta after menu-visibility and heading-level adjustments:

```text
29 passed
```

The initial general close gate before late review/UAT deltas completed with:

```text
make check
All checks passed!
No changes detected
161 passed
```

Two explicit regression tests were later added for `InstitutionalPage` environment noindex/sitemap behavior:

- `SEO_DEFAULT_NOINDEX=True` excludes the institutional page from sitemap URLs;
- `SEO_DEFAULT_NOINDEX=False` includes the eligible institutional page.

The maintainer reported that the focused tests and the full `make check` gate passed after these tests and after the final visual refinements.

After the PR review migration-dependency correction:

- migration validation passed;
- `git diff --check` passed;
- the real push/pre-push path completed successfully;
- Pull Request CI returned green.

No final executable failure remains.

## Diff review and review findings

The complete implementation diff was reviewed once through `tmp/EPIC6-001_diff_review.txt`, including relevant untracked files. The same full content was not re-reviewed by ceremony after staging.

A follow-up review concern about `InstitutionalPage` noindex/sitemap behavior was checked against the real checkout. The production implementation already contained the required `get_sitemap_urls()` behavior, so no production-code change was necessary. Two regression tests were added to make the behavior explicit.

The Pull Request review then identified one valid P1 migration compatibility finding: the generated third-party migration dependency targeted a Wagtail migration node newer than the project's declared minimum supported Wagtail version. The dependency was corrected from Wagtail `0097` to `0094`, validated, pushed, and rechecked by CI. The review finding was resolved and no unresolved review finding remains.

## Failures and root causes

No implementation or test failure remains.

The first sandboxed `docker compose ps` probe during implementation could not access the host Docker socket. This was an execution-permission boundary, not a repository defect; the approved Docker invocation succeeded. Repeated retries were not used.

`makemigrations` emitted the existing Treebeard future-compatibility warnings about Wagtail collection/page managers and Treebeard 6. The migration generated successfully, migration checks passed, and the full test suite remained green. This warning was pre-existing and remains non-blocking under the project's current disposition.

The only material PR review defect was the migration dependency described above. Its root cause was that a generated migration reflected the currently resolved Wagtail 7.4.2 migration graph while the repository advertises support for the broader `>=7.0,<8.0` range. The fix changed only the migration dependency node, not the schema operation.

## Manual validation and maintainer UAT

The maintainer completed browser UAT after applying the migration.

Validated successfully:

1. Home with existing real public news.
2. The newest public story appears as the single featured story.
3. Secondary cards continue after the featured story without duplication.
4. Public news listing at `/noticias/`.
5. Filtering by a real populated section.
6. Empty-state behavior for sections without results.
7. Safe HTTP 200 behavior for an unknown section slug.
8. News detail with featured image, structured body image, caption, credit, YouTube, Spotify, tags, public credits, and existing SEO behavior.
9. Public navigation based on real sections and eligible institutional pages.
10. Institutional page creation below Home.
11. Institutional page behavior outside the menu and after enabling `show_in_menus`.
12. Representative desktop and mobile responsive behavior.
13. Keyboard navigation and the responsive navigation menu.
14. Public surfaces did not expose internal contributor or privacy fields.

Two visual observations were found during UAT:

- the `Últimas noticias` section on Home needed slightly more spacing above it;
- YouTube embeds in the article body appeared too short vertically.

The Home secondary-news section received additional top spacing, and public article iframes were changed to use a responsive 16:9 aspect ratio. Both visual corrections were rechecked successfully in the browser, and the subsequent general check passed.

No formal WCAG audit or final visual-design approval is claimed.

## Pull Request and CI

The ticket was committed and pushed on its feature branch, then opened as a Pull Request against `main`.

The configured CI validation completed successfully after the implementation and again after the review correction. The valid Codex PR review finding was resolved, and the Pull Request reached a green state with no known unresolved finding before this final feedback replacement.

This feedback is intentionally finalized once at the stable Stage B boundary instead of being rewritten after every commit, push, CI transition, or review event.

## Warnings and accepted deferred work

- Bootstrap and its bundle require access to jsDelivr at runtime. The dependency is centralized and provisional, and no current repository policy contradicts it.
- The visual treatment is intentionally a replaceable editorial mockup, not a final brand identity.
- A formal accessibility audit remains outside this ticket. The completed UAT covers only the basic responsive, semantic, focus, and keyboard behavior required by the approved scope.
- The existing Treebeard future-compatibility warning remains non-blocking and should be reevaluated only under its existing roadmap conditions.

## Privacy, data, and scope review

The changed public paths use only live/public Wagtail pages and editor-controlled public credits. Tests exercise internal minor relationships and privacy flags and confirm they do not appear on Home, list, or detail.

No fixtures, seed data, data migrations, management commands, secrets, credentials, production values, or automatic institutional/news content were added. Test content is fictitious and non-sensitive.

No unrelated deployment, role, permission, full-text search, geographic filter, workshop system, form, page builder, React/Next.js frontend, Tailwind setup, or advanced institutional CMS feature was introduced.

## New Work Discovered

No blocking new work was discovered.

The following remain separate future concerns and were already outside the approved ticket:

- final brand and UX pass;
- formal accessibility audit;
- locally hosted frontend assets if a future security policy requires them;
- advanced institutional CMS capabilities;
- workshop management.

The PR review also produced one durable technical lesson rather than a new feature ticket: generated migrations that depend on third-party migration nodes must be checked against the project's declared supported dependency range, not only against the currently resolved framework version.

## Durable knowledge candidates

### Technical context

Consolidate the durable public architecture introduced by EPIC6-001:

- shared public layout in `templates/base.html`;
- replaceable public visual layer in `templates/includes/` and `static/public/css/site.css`;
- Bootstrap 5.3.3 loaded centrally from jsDelivr with SRI;
- shared public news selector in `apps.news.selectors.public_news_pages`;
- public list route `/noticias/`;
- section-filter contract `?seccion=<slug>`;
- `InstitutionalPage` under `HomePage`, with no child pages;
- public institutional navigation limited to direct Home children that are live, public, and `show_in_menus`;
- migration review must account for the lower bound of supported third-party framework versions when dependency nodes are serialized.

### Roadmap

EPIC6-001 should be marked completed. The roadmap should be reconciled because this approved vertical slice delivered capabilities that the older roadmap had split across several provisional EPIC6 candidates:

- shared layout/navigation/footer;
- Home editorial hierarchy;
- public news listing and section filtering;
- renewed news detail;
- simple Wagtail institutional pages;
- responsive/accessibility baseline.

Future EPIC6 work should be re-evaluated from the implemented state rather than assuming those older candidates remain untouched.

### Execution process

Preserve these process rules:

- successful preparatory steps do not need to be pasted to or re-reviewed by the follow-up chat; the maintainer shares preparation output only when an error occurs;
- complete relevant diff content is reviewed once, and later narrow deltas are reviewed or validated proportionally;
- Stage A feedback remains a draft during implementation;
- late evidence from UAT, commit/push, PR, CI, and review is consolidated once into one complete downloadable `Closing Feedback Final` replacement before merge;
- the maintainer should not manually merge feedback fragments section by section.

The existing execution guide already defines the single Stage B replacement rule. Future handoffs should enforce it rather than reintroducing incremental feedback edits.

## Final closure state

At the time this `Closing Feedback Final` replacement is prepared:

- implementation is complete;
- required migration was applied locally for UAT;
- maintainer UAT passed;
- final visual observations were corrected and rechecked;
- automated validation is green;
- the Pull Request is green;
- the valid review finding is resolved;
- no known blocking or unresolved ticket finding remains.

The remaining maintainer actions are the final feedback-only commit/push, the required latest CI completion for that commit when applicable, and the normal Squash and merge operation.
