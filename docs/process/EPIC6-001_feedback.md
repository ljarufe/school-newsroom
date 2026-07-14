# EPIC6-001 Feedback

## Status

Implementation Closing Draft

## Implementation summary

EPIC6-001 adds a navigable, responsive public vertical slice without adding
demo content or a separate frontend build. Home, the public news list, news
detail, and institutional pages now extend one public base layout with Spanish
landmarks, keyboard-visible focus, a skip link, responsive navigation, and a
common footer.

Bootstrap 5.3.3 is loaded centrally from jsDelivr with Subresource Integrity
and `crossorigin="anonymous"`. Project styling is isolated in
`static/public/css/site.css`. The Bootstrap imports and this stylesheet are the
replaceable provisional visual layer; no Node, React, Next.js, Tailwind, or
asset-build dependency was introduced. The repository has no Content Security
Policy or asset rule that contradicts CDN-hosted provisional assets.

Home and the new list view share `public_news_pages()`, which applies
`live().public()`, selects section, school, and featured image, prefetches only
ordered public credits, and orders by `-publication_date` then
`-first_published_at`. Home evaluates at most 12 records, assigns the first to
`featured_news`, and assigns the remaining records to `secondary_news`, so the
featured story cannot be duplicated. Both surfaces render explicit empty
states and never manufacture cards or content.

The public list route is `/noticias/`. Its filter contract is
`?seccion=<NewsSection.slug>`. No filter lists all public news; a valid section
filters the same public query; a valid section without results renders a
section-specific empty state; and an unknown slug returns HTTP 200 with a safe,
clear error state and a link back to the complete list.

Public navigation is prepared by a template tag from real `NewsSection`
records and direct institutional children of the current site Home that are
live, public, and marked `show_in_menus`. Missing, draft, restricted, or
menu-disabled institutional pages do not create placeholders. Sections link to
the list filter; no Wagtail section pages were added.

News detail keeps the existing canonical, robots, Open Graph, Twitter/X, and
safe JSON-LD blocks. Existing public fields, ordered public credits, featured
image, structured body, article-image alt/caption/optional credit,
YouTube/Spotify output and fallbacks, and tags remain present. No public query
or template loads internal contributor relations, and no internal minor name,
age band, or privacy flag is rendered.

## Files changed

- `apps/home/models.py`: Home page context split and `InstitutionalPage`.
- `apps/home/migrations/0003_institutionalpage.py`: generated schema migration.
- `apps/home/templatetags/__init__.py`: template-tag package.
- `apps/home/templatetags/public_navigation.py`: real-content public navigation.
- `apps/home/tests.py`: institutional tree, rendering, labels, features, and
  menu visibility tests.
- `apps/news/selectors.py`: shared public-news query and editorial ordering.
- `apps/news/views.py`: public list view and section-filter behavior.
- `apps/news/tests/test_public_rendering.py`: Home split, list filtering,
  visibility/privacy, empty states, and shared-layout tests.
- `config/urls.py`: named `/noticias/` route before Wagtail's catch-all.
- `templates/base.html`: common public document, Bootstrap integration,
  landmarks, footer, and extensible blocks.
- `templates/includes/public_navigation.html`: responsive public navigation.
- `templates/includes/news_card.html`: shared Home/list news card.
- `templates/home/home_page.html`: editorial Home hero, secondary cards, and
  empty state.
- `templates/home/institutional_page.html`: common-layout institutional page.
- `templates/news/news_list.html`: public list/filter and safe empty states.
- `templates/news/news_page.html`: common-layout visual detail preserving SEO.
- `templates/news/blocks/article_image.html`: responsive article-image classes.
- `static/public/css/site.css`: isolated provisional editorial styling.
- `docs/editorial/guia_de_uso.md`: public navigation, institutional authoring,
  real-content verification, and current limitations.

## Migration details

`apps/home/migrations/0003_institutionalpage.py` was generated with Django
5.2.16 against Wagtail 7.4.2. It depends on:

- `home.0002_alter_homepage_options`;
- `wagtailcore.0097_baselogentry_uuid_action_timestamp_indexes`.

Its only operation is `CreateModel(InstitutionalPage)` with Wagtail's native
page pointer, required `introduction`, required `body`, and Spanish model/field
metadata. It contains no `RunPython`, data migration, automatic page creation,
or content creation. `HomePage` allows `NewsPage` and `InstitutionalPage`
children; `InstitutionalPage` allows no children; existing `NewsPage`
constraints are unchanged. Generated repository files remain owned by the host
user. The migration was not applied to the maintainer's persistent database.

## Automated validation

Focused public, institutional, SEO, body-image, and provider behavior:

```text
docker compose run --rm web sh -c "python -c 'import django, wagtail; print(django.get_version(), wagtail.__version__)' && until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/home/tests.py apps/news/tests/test_public_rendering.py apps/news/tests/test_seo_public.py apps/news/tests/test_blocks.py"
5.2.16 7.4.2
56 passed in 6.23s
```

Focused delta after menu-visibility and heading-level adjustments:

```text
docker compose run --rm web sh -c "until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/home/tests.py apps/news/tests/test_public_rendering.py"
29 passed in 5.57s
```

Official lint interface before the close gate:

```text
make lint
All checks passed!
```

General close gate, run once:

```text
make check
All checks passed!
No changes detected
161 passed in 22.51s
```

Whitespace validation:

```text
git diff --check
(no output; exit 0)
```

## Failures and root causes

No implementation or test failure remains.

The first sandboxed `docker compose ps` probe could not access the host Docker
socket. This was an execution-permission boundary, not a repository failure;
the approved Docker invocation succeeded. `makemigrations` also emitted the
existing Treebeard future-compatibility warnings about Wagtail collection/page
managers and Treebeard 6. The migration generated successfully, migration check
reported no pending changes, and the full suite passed. Repeated retries were
not used.

## Manual validation and maintainer UAT

Manual browser UAT was not performed and is deferred to the maintainer. After
reviewing and applying the migration with the normal Docker-first workflow, UAT
should cover:

1. Home with no public news and with one or two manually authored,
   fictitious/non-sensitive public news records.
2. Featured/secondary ordering and absence of featured duplication.
3. The complete list, a populated section, an empty real section, and an
   unknown section slug.
4. News detail with featured/body images, public credits, YouTube, Spotify,
   tags, and SEO metadata.
5. An institutional page created below Home, first outside menus and then
   published with `show_in_menus` enabled.
6. Keyboard navigation, the mobile collapse menu, and representative mobile
   and desktop widths.

No formal WCAG audit or final visual-design approval is claimed.

## Warnings and deferred validation

- Bootstrap and its bundle require access to jsDelivr at runtime. The
  dependency is centralized and provisional, and no current repository policy
  contradicts it.
- The visual treatment is intentionally a replaceable editorial mockup, not a
  final brand identity.
- Browser rendering, CDN availability, responsive visual quality, and complete
  keyboard behavior still require maintainer UAT.
- The persistent local database still requires `make migrate` by the
  maintainer before authoring institutional pages.

## Privacy, data, and scope review

The changed public paths use only live/public Wagtail pages and editor-controlled
public credits. Tests exercise internal minor relationships and privacy flags
and confirm they do not appear on Home, list, or detail. No fixtures, seed data,
data migrations, management commands, secrets, credentials, production values,
or automatic institutional/news content were added. Test content is explicitly
fictitious and non-sensitive. No unrelated feature, deployment, role,
permission, search, geographic filter, workshop system, form, or page builder
was introduced.

## New Work Discovered

No blocking new work was discovered. A final brand/UX pass, a formal
accessibility audit, locally hosted frontend assets if future security policy
requires them, advanced institutional CMS features, and workshop management
remain separate future concerns already outside this approved ticket.

## Durable knowledge candidates

- Keep public news visibility, eager loading, public-credit ordering, and
  editorial ordering centralized in `apps.news.selectors.public_news_pages`.
- Keep the section-filter URL contract at `/noticias/?seccion=<slug>` unless a
  later routing ticket intentionally changes it.
- Public institutional navigation is based on direct Home children that are
  live, public, and `show_in_menus`; it is not a generic menu-builder system.
- The public visual layer is intentionally concentrated in `templates/base.html`,
  `templates/includes/`, and `static/public/css/site.css` for replacement.
- Successful preparatory steps do not need to be pasted to or re-reviewed by a
  follow-up chat. The maintainer should share preparation output only when an
  error occurs; redundant verification after successful preparation should be
  avoided.

## Final Git status

The authoritative close status is also captured in
`tmp/EPIC6-001_diff_review.txt`. No files are staged, and no commit, push, pull
request, or merge was performed.
