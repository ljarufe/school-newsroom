# Guía de uso editorial

## Acceso

Wagtail Admin local:

```text
http://localhost:8000/admin/
```

Home pública local:

```text
http://localhost:8000/
```

## Secciones editoriales

Ruta en Wagtail Admin:

```text
Editorial -> Secciones editoriales
```

Una sección editorial clasifica una noticia dentro de la cobertura del sitio.
Las secciones iniciales son:

- Política
- Cultura
- Medio Ambiente
- Problemáticas Sociales
- Columnas
- Entrevistas

## Colegios

Ruta en Wagtail Admin:

```text
Editorial -> Colegios
```

Un colegio representa una institución educativa que puede asociarse a una
noticia. Los campos actuales son:

- Nombre
- Provincia
- Distrito

Provincia y Distrito son campos de texto libre. Actualmente no existe
validación contra datos geográficos oficiales.

## Grupos de colaboradores

Ruta en Wagtail Admin:

```text
Editorial -> Grupos de colaboradores
```

Un grupo de colaboradores organiza internamente a escolares que participan en
un taller, equipo o grupo asociado a un colegio. Los campos actuales son:

- Nombre
- Colegio

El nombre es libre y editable. En esta versión no existe todavía un modelo
separado para grado, sección, cohorte, ciclo de taller o responsabilidad.

## Colaboradores menores

Ruta en Wagtail Admin:

```text
Editorial -> Colaboradores menores
```

Un colaborador menor es un registro interno mínimo para trazabilidad editorial.
Los campos actuales son:

- Nombre interno
- Grupo
- Franja de edad

La franja de edad sólo distingue:

- Menor de 14 años
- De 14 a 17 años

No se registra fecha de nacimiento, edad exacta, DNI, contacto, datos de padre,
madre o tutor, ni documentos de autorización. El colegio se obtiene desde el
grupo seleccionado; no se duplica en el colaborador.

El nombre interno no se publica automáticamente.

## Noticias

Ruta para crear una noticia:

```text
Páginas -> Inicio -> Añadir página hija -> Noticia
```

Campos principales:

- Título
- Fecha de publicación
- Resumen
- Contenido
- Sección
- Colegio
- Cobertura
- Imagen destacada
- Etiquetas
- Colaboradores internos
- Firma pública
- Privacidad de menores

La ubicación del colegio describe dónde está la institución educativa asociada.
La cobertura editorial describe el territorio sobre el que trata la noticia.
Pueden coincidir, pero no son el mismo dato.

## Colaboradores internos y firma pública

En una noticia, `Colaboradores internos` y `Firma pública` son datos distintos.

`Colaboradores internos` permite asociar uno o más colaboradores menores ya
registrados. Esta relación es para trazabilidad editorial interna y no se
muestra en la Home ni en el detalle público.

`Firma pública` contiene el texto que el editor decide mostrar como autoría
pública. Puede haber varias firmas y se muestran en el orden definido por el
editor. Ejemplos de firmas posibles:

- Grupo de periodismo del taller del 5to A de secundaria del Colegio de prueba
- A. Prueba U. del 5to A de secundaria, Colegio de prueba
- Equipo escolar de La Unión
- Marco Zavalaga, editor responsable

El CMS no deriva una firma pública desde el nombre interno del colaborador, el
colegio ni el usuario editor.

Guardar como borrador permite dejar la firma pública vacía. Para publicar,
programar o enviar a workflow, la noticia debe tener al menos una firma pública
efectiva.

## Privacidad de menores

El panel `Privacidad de menores` incluye tres marcas editoriales:

- `Contiene menores identificables`: se usa cuando la noticia puede identificar
  a menores por nombre o firma pública, imagen reconocible, voz, video u otra
  información.
- `Confirmo que se verificaron las autorizaciones requeridas para exponer
  públicamente a los menores identificables de esta noticia`: declaración
  operacional del editor para esa noticia.
- `Contenido sensible`: señal editorial para contenido social, denuncia u otro
  tratamiento delicado que requiere especial criterio editorial.

Cuando `Contiene menores identificables` está marcado, el editor debe confirmar
que verificó las autorizaciones requeridas antes de publicar, programar o enviar
a workflow. Los documentos de autorización no se almacenan todavía en el CMS.

`Contenido sensible` no bloquea por sí solo la publicación. Tener colaboradores
internos menores tampoco exige por sí solo marcar la confirmación de
autorizaciones; el bloqueo depende de declarar que la noticia contiene menores
identificables.

El panel enlaza a la fuente oficial usada como referencia informativa:

```text
https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=23
```

El aviso del Admin resume que el Reglamento de la Ley N.º 29733 contempla
criterios diferenciados para menores de 14 años y adolescentes de 14 a 17 años.
La política de Noticias es conservadora: la exposición pública de cualquier
menor identificable requiere verificación editorial de autorizaciones según la
política del proyecto. Esta guía no sustituye revisión legal profesional.

## Contenido estructurado

El campo Contenido acepta estos bloques:

- Párrafo
- Imagen
- Video de YouTube
- Audio o pódcast de Spotify

`Párrafo` permite escribir prosa larga con varios párrafos dentro del mismo
bloque. También permite negrita, cursiva, enlaces, encabezados H2, H3 y H4,
listas numeradas, listas con viñetas, citas, líneas horizontales y enlaces a
documentos del CMS.

Selecciona texto para mostrar la barra contextual de formato. El pin de esa
barra permite mantenerla visible; Wagtail recuerda la preferencia en ese
navegador. Pulsa `/` para abrir la paleta de comandos y las acciones de bloque
disponibles. La acción `Split block` se encuentra en esa superficie y divide el
bloque en la posición del cursor; no aparece como botón permanente.

El editor reconoce algunos atajos de escritura tipo Markdown para los formatos
habilitados, pero no es un editor Markdown general. Escribe estos patrones al
inicio de una línea y añade el espacio indicado para los formatos de bloque. En
negrita y cursiva, escribe también el marcador de cierre.

| Resultado | Atajo de escritura |
| --- | --- |
| H2 | `## ` |
| H3 | `### ` |
| H4 | `#### ` |
| Lista con viñetas | `* ` o `- ` |
| Lista numerada | `1. ` |
| Cita | `> ` |
| Línea horizontal | `---` |
| Negrita | `**texto**` o `__texto__` |
| Cursiva | `*texto*` o `_texto_` |

Los enlaces normales y los enlaces a documentos se insertan desde la barra de
formato. Las imágenes y el contenido multimedia externo no se insertan desde
esa barra.

El bloque `Imagen` inserta una imagen dentro del cuerpo de la noticia, distinta
de la `Imagen destacada`. Se usa este bloque separado para que cada uso tenga un
pie de foto obligatorio, un texto alternativo contextual obligatorio y un
crédito opcional. Sus campos son:

- Imagen
- Pie de foto
- Texto alternativo
- Crédito de imagen

`Pie de foto` se muestra públicamente. `Texto alternativo` se usa como atributo
`alt` de la imagen y no se imprime como texto visible adicional. `Crédito de
imagen` es opcional y sólo se muestra cuando tiene contenido.

Al crear o reabrir una imagen del cuerpo, el Admin ayuda copiando el pie de foto
al texto alternativo como punto de partida mientras el texto alternativo no haya
sido personalizado. Si el editor cambia manualmente el texto alternativo,
cambios posteriores del pie de foto ya no lo sobrescriben para ese bloque.

Guardar como borrador permite dejar incompleta una imagen del cuerpo. Para
publicar, programar o enviar a workflow, la imagen, el pie de foto y el texto
alternativo deben estar completos; espacios en blanco no cuentan como contenido
efectivo.

`Video de YouTube` acepta URLs compatibles de YouTube. `Audio o pódcast de
Spotify` acepta URLs compatibles de Spotify. Si una URL no pertenece al
proveedor del bloque, la validación la rechaza. Si una URL previamente válida
deja de resolverse como contenido multimedia público, la noticia muestra un
enlace a la URL original con una etiqueta del proveedor. No uses una inserción
multimedia genérica dentro de `Párrafo`.

## Borrador y publicación

Guardar como borrador conserva la noticia dentro de Wagtail Admin sin mostrarla
en la Home pública anónima.

Publicar la noticia mediante Wagtail la hace visible en la Home pública. Desde
la Home, el título de la noticia abre su página pública de detalle.

La publicación, programación o envío a workflow se bloquea cuando:

- falta una firma pública efectiva;
- una imagen del cuerpo no tiene imagen, pie de foto o texto alternativo
  efectivo;
- `Contiene menores identificables` está marcado y no se confirmó la
  verificación de autorizaciones.

Cuando `Contenido` tiene un error, el resumen de la página indica que se deben
revisar los bloques marcados. El bloque afectado muestra el detalle específico,
por ejemplo qué campo falta en una imagen.

## Limitaciones actuales

- No hay flujo editorial personalizado todavía.
- No hay roles ni permisos personalizados todavía.
- No hay cuentas de estudiantes, docentes, monitores ni tutores todavía.
- No hay responsabilidades individuales por fotografía, investigación,
  redacción u otras labores todavía.
- No hay perfil público reusable de autor todavía.
- No hay tipos persistidos de firma pública todavía.
- No hay carga ni seguimiento individual de documentos de autorización todavía.
- Provincia y Distrito no se validan todavía contra datos geográficos oficiales.
- No hay SEO Assistant todavía.
- No hay análisis automático de rostros, voces, proveedores externos ni datos
  personales dentro de imágenes, video o audio.
