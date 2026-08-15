# Peru UBIGEO snapshot (2025-12-31)

This directory contains the normalized territorial catalog used by the application and
by the historical data migration. The raw workbook is not versioned because it also
contains population projections that the product does not use.

## Provenance

- Authority: Instituto Nacional de Estadística e Informática (INEI).
- Official publication: *Perú: Población Total Proyectada al 30 de Junio de cada
  año, según Departamento, Provincia y Distrito, 2018-2026*.
- Publication page:
  `https://www.gob.pe/institucion/inei/informes-publicaciones/6894980-peru-poblacion-total-proyectada-al-30-de-junio-de-cada-ano-segun-departamento-provincia-y-distrito-2018-2026`
- Resolved official resource URL:
  `https://cdn.www.gob.pe/uploads/document/file/8261096/6894980-peru-poblacion-total-proyectada-al-30-de-junio-de-cada-ano-segun-departamento-provincia-y-distrito-2018-2026.xlsx?v=1768402069`
- Cutoff/publication date: 2025-12-31.
- Raw XLSX size: 212,580 bytes.
- Raw XLSX SHA-256:
  `9436df29b883fd4a9db3705040a6668ff4efe7047c2643249b6b6bedd90d5c8b`.
- Normalized CSV SHA-256:
  `58a2959fa22fd9ff3b515a357f451e26a56f82178dfa363f64499d996fb0fff3`.
- License status: License not explicitly stated on the selected INEI
  publication/resource.

The maintainer approved using this official resource with the documented provenance
limitation. No license was inferred from another INEI dataset.

## Validation and transformation

The workbook worksheet `POB. PROYECTADA 2018-2026` exposes the six-character
`UBIGEO` code in column A and the territorial name in column B. The snapshot was
generated with `openpyxl` from the raw official bytes, preserving codes as strings.

The deterministic transformation:

1. excludes the national `000000` row, headers, population columns and notes;
2. derives department codes from `DD0000`, province codes from `DDPP00`, and
   district codes from `DDPPDD`;
3. trims and collapses whitespace, removes workbook footnote suffixes such as
   `12/`, and converts uppercase source names to display case while retaining the
   source spelling;
4. emits one row per district in code order with its department and province.

Validated snapshot counts:

- 25 department-level units (24 departments plus Callao);
- 196 provinces;
- 1,892 districts;
- no duplicate codes;
- no orphan provinces or districts;
- Arequipa department code `04`.

Do not replace this file in place after a migration references it. A future reviewed
snapshot must use a new dated filename and a new migration.
