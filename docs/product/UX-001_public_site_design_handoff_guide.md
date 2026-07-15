# Public Site Design Deliverables Guide

File specifications, visual foundations, responsive behavior, components, screens, assets, and handoff requirements.

The purpose of this guide is to ensure the design can be implemented without guessing values, variants, assets, or responsive behavior.

> **Scope: public MVP in light mode. The design file must be editable, inspectable, and prepared for handoff.**

# 1. Objective and deliverables

Define the visual system and the current public-site screens with enough specification to reproduce the design in development without inferring colors, typography, measurements, spacing, responsive behavior, or assets.

## Required deliverables

> **1.** Editable design file, preferably in Figma.
>
> **2.** Visual foundations with exact values: color, typography, spacing, grid, containers, borders, radii, and shadows when used.
>
> **3.** Reusable components with variants and states.
>
> **4.** Final mobile and desktop screens; tablet when a layout change cannot be clearly inferred.
>
> **5.** Exportable final assets: logo, used brand variants, custom iconography, and required graphic resources.
>
> **6.** Font specification, including weights, source, and licensing.
>
> **7.** Behavior notes only when a decision is not evident from the design itself.
>
> **8.** Visible identification of material that is ready for development.

> **A collection of flat screenshots is not a sufficient handoff: visual values and assets must be explicitly inspectable or documented.**

# 2. Design file

## Preferred format

The preferred option is an editable Figma file. An equivalent tool may be used if it allows exact values to be inspected, components and variants to be identified, responsive behavior to be reviewed, assets to be exported, and final designs to be clearly separated from explorations.

## The file must allow inspection of

- dimensions and position;

- padding and gap;

- colors;

- font family, weight, size, line-height, and letter-spacing;

- radii, borders, and shadows;

- components and variants;

- assets configured for export.

## Recommended structure

| **Section** | **Content** |
|---|---|
| 00 | Cover and delivery status |
| 01 | Visual foundations |
| 02 | Components |
| 03 | Home |
| 04 | News listing |
| 05 | News detail |
| 06 | Institutional page |
| 07 | States and 404 |
| 08 | Explorations, only if they exist |

## Semantic naming

Use stable, descriptive names for sections, frames, and components. Keep one clearly identified final version per viewport and separate explorations from material that is ready for development.

| **Preferred** | **Avoid** |
|---|---|
| Foundations / Color | Frame 123 |
| Component / News Card / Primary | Card 7 |
| Page / Home / Desktop / Final | Final final |
| Page / News Detail / Mobile / Final | Copy 4 |

![Visual reference](assets/ux-001/file-organization-example.png)

Example of file organization and separation between final material and explorations.

# 3. Visual foundations

Visual foundations must be defined with exact names and values. The examples in this section show the expected level of precision; their values are illustrative.

## 3.1. Color

Deliver each color with a semantic name, exact value, and purpose. When a color changes through interaction, document the relationship between its states.

| **Name** | **Value** | **Primary use** |
|---|---|---|
| Color / Brand / Primary | `#______` | Brand and primary accent |
| Color / Background / Page | `#______` | Page background |
| Color / Background / Surface | `#______` | Surfaces |
| Color / Text / Primary | `#______` | Primary text |
| Color / Text / Secondary | `#______` | Metadata |
| Color / Border / Default | `#______` | Borders and dividers |
| Color / Link / Default | `#______` | Links |
| Color / Focus | `#______` | Focus indicator |

- Use HEX for solid colors intended for the web.

- Specify RGBA or explicit opacity when transparency is used.

- Define all values and direction when a gradient is used.

- Document Default, Hover, Active, and Focus when they change visually.

![Visual reference](assets/ux-001/color-specification-example.png)

Example of palette specification and interactive states.

## 3.2. Typography

Identify each typeface, its source, license, purpose, weights, styles, and fallback. The type scale must provide exact values per viewport when they change.

| **Field** | **Specification** |
|---|---|
| Exact name | |
| Provider or source | |
| License | |
| Use | Headings / reading / interface / other |
| Weights used | Example: 400, 500, 700 |
| Styles used | Normal / italic |
| Web fallback | Example: `"Name", Arial, sans-serif` |

The type scale must cover at least H1, H2, H3, body, small text, metadata, captions, credits, navigation, and controls that use a distinct style. For each style, specify family, weight, size, line-height, and letter-spacing.

![Visual reference](assets/ux-001/typography-specification-example.png)

Example of a font-family sheet and implementation-ready type scale.

## 3.3. Spacing

Define a reusable scale for padding, gap, separation between related elements, separation between sections, and vertical margins in editorial content.

| **Name** | **Value** |
|---|---|
| Space / 1 | `__ px` |
| Space / 2 | `__ px` |
| Space / 3 | `__ px` |
| Space / 4 | `__ px` |
| Space / 5 | `__ px` |
| Space / 6 | `__ px` |

When an exceptional value does not belong to the scale, identify it in the component or layout where it is used.

![Visual reference](assets/ux-001/spacing-specification-example.png)

Example of a spacing scale and application of values inside a component.

## 3.4. Grid, containers, and widths

Define the layout structure by viewport and document content and reading maximum widths separately.

| **Reference viewport** | **Columns** | **Side margin** | **Gutter** | **Max. container** |
|---|---:|---:|---:|---:|
| Mobile | | | | |
| Tablet, if applicable | | | | |
| Desktop | | | | |

| **Measurement** | **Value** |
|---|---:|
| Maximum overall content width | |
| Maximum article reading width | |
| Maximum institutional content width | |
| Multimedia width or behavior | |

The current implementation uses Bootstrap 5. The designer does not need to specify technical classes, but a conventional responsive grid makes the design easier to translate. On desktop, a 12-column grid is the most direct implementation reference. Any composition that intentionally departs from the main grid must be identified.

![Visual reference](assets/ux-001/grid-containers-example.png)

Example of columns, margins, gutters, and container specification by viewport.

## 3.5. Borders, radii, and shadows

Document only the properties used in the final design.

- Radii: name, value, and use.

- Borders: width, style, and color.

- Shadows: name, x, y, blur, spread, color/opacity, and components where they are used.

![Visual reference](assets/ux-001/borders-radii-shadows-example.png)

Example of radii, borders, and surface-effect specification.

## 3.6. Brand, logo, and iconography

### Site name

The design must show the brand name used on the site and its relationship with the logo. If the public name has not yet been approved, mark it as provisional and avoid embedding it irreversibly inside a raster asset.

### Logo

Deliver only the variants that are actually used. For each variant, specify name, use, intended background, final format, clear space, and minimum size when applicable. The preferred format for vector logos is SVG with a transparent background and a correct `viewBox`.

### Iconography

If an existing library is used, identify its name, source, and license. If custom icons are created, deliver each final icon as SVG and keep a consistent size and stroke system.

![Visual reference](assets/ux-001/brand-logo-iconography-example.png)

Example of a logo and iconography sheet and asset-export structure.

# 4. Responsive

## Design viewports

| **Viewport** | **Deliverable** |
|---|---|
| Mobile | Representative final frame between 360 and 430 px. |
| Desktop | Representative final frame between 1200 and 1440 px. |
| Tablet | Around 768 px when there is a material change that cannot be inferred between mobile and desktop. |

A consistent reference width is recommended across all pages in the same family, for example 390 px, 768 px, and 1440 px. These sizes are design frames, not the only widths the real site will support.

## Changes that must be defined

- number of columns;

- element order and alignment;

- relative width of blocks;

- image behavior and proportions;

- typography changes;

- padding or gap changes;

- components that change from horizontal to vertical;

- menu behavior;

- hidden elements, only when applicable.

When the change is evident in the final frames, it does not need to be repeated in a note. Annotate only behavior that cannot be inferred visually.

![Visual reference](assets/ux-001/responsive-handoff-example.png)

Example of a responsive handoff with reference frames and transition rules between sizes.

# 5. Components

Each reusable component must be defined through its variants and states. A separate written specification is not required when the information can be clearly inspected in the component and its properties.

| **Field** | **Content** |
|---|---|
| Name | Semantic name |
| Anatomy | Parts that compose it |
| Variants | Real structural differences |
| States | Default, hover, focus, active, etc. |
| Size | Fixed, fluid, or container-dependent |
| Responsive | Changes between viewports |
| Variable content | Which elements may grow, be absent, or wrap |
| Assets | Associated icons or images |

## Minimum components

| **Group** | **Components** |
|---|---|
| Navigation | Header, desktop navigation, mobile menu, active link if used, brand identity, and footer. |
| News | Primary card, secondary card, listing card/item, with-image and without-image variants, section badge, date, credits, and summary when applicable. |
| Editorial content | Article header, featured image, reading body, H2, H3, links, figure, caption, credit, YouTube, and Spotify. |
| Interaction | Primary button, secondary button if used, text link, hover, focus, and active when applicable. |
| States | General empty state and filter-with-no-results state. |
| Institutional | Generic institutional page pattern. |

![Visual reference](assets/ux-001/component-specification-example.png)

Example of anatomy, variants, states, and variable-content behavior in a reusable component.

# 6. Final screens

Each surface must be delivered as a final mobile and desktop frame. Tablet is included only when it adds an additional layout decision.

## 6.1. Home

- primary story;

- secondary stories;

- navigation and footer;

- news components used;

- with-image and without-image variants when applicable.

## 6.2. News listing

- normal state;

- active section filter;

- no-results state;

- mobile and desktop.

## 6.3. News detail

- editorial header and metadata;

- featured image when present;

- reading body;

- H1, H2, and H3;

- body images, caption, and credit;

- YouTube and Spotify;

- links and tags when present.

The reading width, vertical content spacing, typographic hierarchy, and treatment of images and multimedia must be defined.

## 6.4. Generic institutional page

- title;

- introduction when present;

- body;

- subheadings;

- links;

- mobile and desktop.

## 6.5. Navigation, footer, and states

- desktop header;

- mobile menu closed and open;

- footer;

- empty state;

- filter with no results;

- 404 page, optional.

> **Highly customized interactions or compositions must be marked as `Requires technical validation` before they are considered committed for implementation.**

# 7. Assets and handoff

## Final asset package

Every resource required to reproduce the design must be identified, marked as final, exportable, and separated from resources used only for mockups.

| **Type** | **Preferred format** |
|---|---|
| Logos, icons, and vector illustrations | SVG |
| Final raster optimized for the web | WebP |
| Raster with transparency or a specific need | PNG |
| Photography when appropriate | JPEG or WebP |
| Font hosted by the project, when licensing allows | WOFF2 |

## Fonts

Specify exact name, weights and styles used, provider, license, and intended usage method. Do not deliver weights that are not used in the design. Do not introduce a commercial font without informing the team about its license.

## Design states

| **State** | **Meaning** |
|---|---|
| Ready for development | Final design approved for implementation. |
| In exploration | Alternative or work that is not yet resolved. |
| Future proposal | Idea outside the current scope. |
| Requires technical validation | Design or interaction that must be reviewed before implementation is committed. |

## Handoff notes

Add notes only when the design does not communicate a relevant decision by itself, for example:

- non-obvious responsive behavior;

- image crop rule;

- element that changes position;

- exceptional variant;

- interaction;

- external asset;

- variable-text behavior;

- grid exception.

## Final delivery

> **1.** Link to the editable design file.
>
> **2.** Direct links to final sections or frames when the tool allows it.
>
> **3.** Final assets.
>
> **4.** Font and licensing information.
>
> **5.** Identification of material that is ready for development.
>
> **6.** Short list of decisions that remain open, if any.

# 8. Current site context

The design applies to the existing public surfaces. The following screenshots are references for identifying the content and surfaces that must be redesigned.

## Existing surfaces

> **1.** Home.
>
> **2.** News listing at `/noticias/`.
>
> **3.** News-list section filter.
>
> **4.** News detail.
>
> **5.** Generic institutional page.
>
> **6.** Header and navigation.
>
> **7.** Footer.
>
> **8.** Empty states.
>
> **9.** 404 page, optional within this engagement.

Editorial sections work as navigation and filtering; they are not independent pages.

![Visual reference](assets/ux-001/current-public-surfaces-reference.png)

Reference for the current public surfaces.

## Content the components must support

- news with and without an image;

- short and long titles;

- one or multiple public credits;

- detail pages with and without a featured image;

- long-form article content;

- body image with caption and credit;

- YouTube block;

- Spotify block.

![Visual reference](assets/ux-001/current-multimedia-detail-reference.png)

Reference for the current detail page with body images, YouTube, and Spotify.

## Scope limits

The following are not part of the design committed for this engagement:

- contact form;

- social sharing;

- new pagination;

- advanced search;

- workshop system;

- newsletter;

- dashboard;

- mobile app;

- Wagtail Admin;

- dark mode;

- separate frontend.

If any of these ideas appear as an exploration, they must remain outside screens marked as `Ready for development`.

# 9. Final delivery checklist

## File and structure

- [ ] Editable file shared.
- [ ] Sections and frames use semantic names.
- [ ] One identifiable final version per viewport.
- [ ] Explorations separated from final material.
- [ ] Final frames marked as `Ready for development`.

## Visual foundations

- [ ] Colors include name, exact value, and use.
- [ ] Interactive color states are defined when applicable.
- [ ] Typeface families, weights, styles, source, and license are identified.
- [ ] Type scale includes size, line-height, and letter-spacing when applicable.
- [ ] Spacing scale is defined.
- [ ] Grid, gutters, and side margins are defined by viewport.
- [ ] Maximum container width and maximum reading width are defined.
- [ ] Radii, borders, and shadows are defined when used.

## Brand and assets

- [ ] Brand name used in the design is identified.
- [ ] Final logo is exportable.
- [ ] Used logo variants are identified.
- [ ] Custom iconography is exportable.
- [ ] Icon libraries and licenses are identified when used.
- [ ] Final raster assets are identified.
- [ ] Mockup assets are separated from interface assets.
- [ ] Fonts and licenses are identified.

## Components

- [ ] Header and desktop navigation.
- [ ] Mobile menu.
- [ ] Footer.
- [ ] Primary card.
- [ ] Secondary card.
- [ ] Listing item or card.
- [ ] With-image and without-image variants.
- [ ] Section badge and metadata.
- [ ] Article header.
- [ ] Figure with caption and credit.
- [ ] YouTube and Spotify.
- [ ] Buttons and links used.
- [ ] Hover and focus.
- [ ] Empty state and filter with no results.
- [ ] Institutional pattern.

## Screens and responsive behavior

- [ ] Home mobile and desktop.
- [ ] News listing mobile and desktop.
- [ ] Active filter state.
- [ ] No-results state.
- [ ] News detail mobile and desktop.
- [ ] Institutional page mobile and desktop.
- [ ] Mobile menu open.
- [ ] Tablet where there is an additional material decision.
- [ ] Non-obvious responsive changes are annotated.

## Handoff

- [ ] Assets configured for export or delivered.
- [ ] Direct links to final frames are available.
- [ ] Notes are added only where necessary.
- [ ] Open decisions are recorded.
- [ ] Future proposals are separated.
- [ ] Elements requiring technical validation are identified.
