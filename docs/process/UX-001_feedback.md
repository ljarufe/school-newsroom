# UX-001 — Closing Feedback

## Status

Implementation Closing Draft

## Summary

UX-001 produced a visual and technical handoff guide for the designer responsible for the Noticias / School Newsroom public site. The guide defines the expected delivery format for visual foundations, responsive behavior, components, screens, assets, and handoff without implementing code or expanding product functionality.

The final designer-facing version was prepared as a visual PDF in Spanish. The repository keeps an English, version-controlled Markdown source accompanied by the reference images needed to understand the specification.

## Implementation

The ticket produced:

- a Spanish designer-facing guide for a professional designer;
- an English repository version intended for versioning, technical review, and later use by Codex or another implementer;
- concrete specifications for color, typography, spacing, grid, containers, borders, radii, and shadows;
- brand, logo, iconography, font, and asset-format requirements;
- responsive requirements for mobile, desktop, and tablet when a material layout change exists;
- minimum component requirements and a format for defining variants and states;
- required final surfaces for Home, news listing, news detail, generic institutional pages, navigation, footer, and empty states;
- visible design-status classification as `Ready for development`, `In exploration`, `Future proposal`, or `Requires technical validation`;
- separate visual references for each visual-foundation topic;
- screenshots of the current public surfaces and the news detail with external multimedia;
- a final delivery checklist.

During iteration, content aimed at programmers or internal implementation process was removed from the designer-facing guide, including the design-to-implementation matrix. That material is preserved as durable process knowledge for the later implementation handoff and implementation ticket.

The repository language convention was also corrected during closeout: repository-facing technical documentation and `docs/process/<TICKET-ID>_feedback.md` are kept in English, while the external designer-facing PDF remains in Spanish.

## Files changed

Expected in the repository:

- `docs/product/UX-001_public_site_design_handoff_guide.md`
- `docs/product/assets/ux-001/file-organization-example.png`
- `docs/product/assets/ux-001/color-specification-example.png`
- `docs/product/assets/ux-001/typography-specification-example.png`
- `docs/product/assets/ux-001/spacing-specification-example.png`
- `docs/product/assets/ux-001/grid-containers-example.png`
- `docs/product/assets/ux-001/borders-radii-shadows-example.png`
- `docs/product/assets/ux-001/brand-logo-iconography-example.png`
- `docs/product/assets/ux-001/responsive-handoff-example.png`
- `docs/product/assets/ux-001/component-specification-example.png`
- `docs/product/assets/ux-001/current-public-surfaces-reference.png`
- `docs/product/assets/ux-001/current-multimedia-detail-reference.png`
- `docs/process/UX-001_feedback.md`

The distribution PDF and editable DOCX are not repository sources of truth and remain outside Git in the project's document storage.

## Validation

Document validation performed during preparation:

- iterative content review with the product owner;
- scope review to prevent new functionality from entering the design engagement;
- consistency review between specifications and visual examples;
- rendering and visual review of the final PDF;
- language review to align repository-facing documentation and ticket feedback with the repository's English technical-documentation convention.

Repository validation still pending at this draft stage:

- review of the real diff after the English replacements;
- `git diff --check`;
- commit and pre-commit;
- push and pre-push;
- Pull Request;
- CI;
- PR review.

Django or browser UAT is not required because this ticket does not modify application code or behavior.

## Failures / retries / root causes

The first approach contained too much product context and too many explanations aimed at development. The root cause was treating the document as a mixed product-and-implementation specification instead of a delivery contract for a professional designer.

The correction reorganized the document around:

- file format;
- inspectable values;
- visual foundations;
- responsive behavior;
- components;
- assets;
- handoff.

The first repository-ready feedback and guide were also prepared in Spanish. This conflicted with the repository convention that technical repository content is written in English. The correction was to keep the external visual deliverable in Spanish while replacing the repository Markdown guide and ticket feedback with English versions.

Visual examples were also split by topic so color, typography, spacing, grid, and other foundations have specific references that can later support implementation.

## Warnings / known limitations

- The final visual design of the public site does not exist yet; this guide defines how it must be delivered.
- The final public brand name may still be open and must be marked as provisional if it is not approved when design work begins.
- A Figma file is not automatically accessible to Codex or another agent; the implementation ticket must provide actual access, direct frame links, or sufficient exports.
- This guide defines the expected structure and quality of the design handoff. It does not replace the future approved design, final Figma file, implementation handoff, or implementation ticket as the source of truth for visual implementation.

## New Work Discovered

### Review and prepare the actual designer deliverable before implementation

**Finding:** receiving a design file does not by itself guarantee that it is ready for implementation.

**Impact:** open decisions, incomplete assets, inconsistencies between viewports, or proposals requiring technical validation may remain.

**Suggested disposition:** create a later design-review/refinement ticket when the real design exists, before the visual implementation ticket if the handoff requires material correction.

### Prepare the design-to-implementation handoff

**Finding:** the mapping between design surfaces and templates/CSS is useful for development but adds noise to the document intended for the designer.

**Impact:** it should live in the context of the later implementation ticket rather than the external designer guide.

**Suggested disposition:** rebuild and validate the matrix against the real checkout when defining the implementation ticket.

### Define a durable source for design work

**Finding:** design and handoff tickets follow a different lifecycle from code tickets and produce reusable knowledge about briefs, deliverables, review, canonical sources, and implementation preparation.

**Impact:** without consolidated guidance, future design work may repeat the same discovery and mix audiences.

**Suggested disposition:** evaluate a new durable design/handoff source or an extension of the existing planning and execution guides, specific to Noticias / School Newsroom but reusable in future projects.

### Optimize validation for documentation-only changes

**Finding:** the current Pull Request validation and local pre-push path run the general technical gate even when a change contains only non-executable documentation and documentation images.

**Impact:** documentation-only tickets can run the complete Django test/lint/migration gate even though their relevant validation is primarily diff review and whitespace/document integrity checks.

**Suggested disposition:** schedule a separate technical/process ticket to classify the real delta and keep one stable required PR check while using a lightweight path for documentation-only changes and the full `make check` path for executable changes. Evaluate the same policy for the local pre-push entry point. Do not solve this through routine `[skip ci]`, manual PR checkboxes, or a workflow-level `paths-ignore` approach that can leave a future required check unresolved.

### Make repository language conventions explicit for process feedback

**Finding:** the repository convention already states that technical repository content is written in English, but the expected language of `docs/process/<TICKET-ID>_feedback.md` was not explicit enough in the working process and the first UX-001 feedback draft was produced in Spanish.

**Impact:** future tickets may repeat the inconsistency.

**Suggested disposition:** update the durable execution/process guidance to state explicitly that repository-facing technical documentation and ticket feedback under `docs/process/` are written in English unless a file has a deliberate user-facing language requirement. Designer-facing, editor-facing, and public-facing deliverables may remain in Spanish when that is their audience.

## Durable knowledge candidates

Candidates for later consolidation:

- separate the designer-facing document from the technical implementation handoff;
- define one canonical source by artifact type: editable visual design in the design tool, visual distribution in document storage, and version-controlled implementation-relevant specification in the repository;
- request explicit semantic values for visual foundations, not screenshots alone;
- keep visual examples next to the specification they illustrate;
- provide the implementation agent with explicit access to the design or sufficient exports;
- review the actual designer deliverable before translating it directly into code when material ambiguity remains;
- keep the design-to-implementation matrix for the technical implementation ticket, not the designer;
- make the English language requirement explicit for repository-facing technical documentation and `docs/process/<TICKET-ID>_feedback.md`;
- evaluate delta-aware validation for documentation-only PRs and pre-push while preserving a stable required status check.

## Deferred closure evidence

To be consolidated once, immediately before merge:

- commit;
- pre-commit;
- push;
- pre-push;
- Pull Request;
- CI;
- review and corrections, if any;
- final merge result.
