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

- Subtítulo
- Párrafo

No hay bloques multimedia personalizados en esta versión.

## Borrador y publicación

Guardar como borrador conserva la noticia dentro de Wagtail Admin sin mostrarla
en la Home pública anónima.

Publicar la noticia mediante Wagtail la hace visible en la Home pública. Desde
la Home, el título de la noticia abre su página pública de detalle.

La publicación, programación o envío a workflow se bloquea cuando:

- falta una firma pública efectiva;
- `Contiene menores identificables` está marcado y no se confirmó la
  verificación de autorizaciones.

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
- No hay bloques multimedia personalizados todavía.
