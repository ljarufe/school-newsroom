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

La ubicación del colegio describe dónde está la institución educativa asociada.
La cobertura editorial describe el territorio sobre el que trata la noticia.
Pueden coincidir, pero no son el mismo dato.

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

## Limitaciones actuales

- No hay flujo editorial personalizado todavía.
- No hay roles ni permisos personalizados todavía.
- No hay flujo de autoría, consentimiento o privacidad estudiantil todavía.
- Provincia y Distrito no se validan todavía contra datos geográficos oficiales.
- No hay SEO Assistant todavía.
- No hay bloques multimedia personalizados todavía.
