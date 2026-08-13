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

Listado público de noticias:

```text
http://localhost:8000/noticias/
```

No compartas cuentas para la operación real. Cada persona adulta debe usar su
propia cuenta. Los escolares pueden figurar como colaboradores internos, pero
no son usuarios del CMS en este MVP.

## Roles del Admin

`Director/editor` puede crear y editar noticias y páginas institucionales,
gestionar los snippets de `Editorial`, trabajar con imágenes y documentos,
revisar privacidad y créditos, usar el Asistente SEO, enviar contenido al
workflow, realizar la revisión editorial final y publicar. No administra
usuarios, grupos ni permisos y no es superusuario.

`Curador SEO` puede entrar al Admin, abrir una tarea activa de `Revisión SEO`,
editar la superficie SEO permitida y elegir una imagen social existente. No ve
la pestaña `Edición de la noticia`, `Propiedades`, `Navegación y menús`,
colaboradores internos ni snippets editoriales; tampoco puede publicar. En
noticias dispone del Asistente SEO completo y ve las secciones y subsecciones
de la noticia como contexto de solo lectura. En `Inicio` y páginas
institucionales dispone sólo de `Slug de la URL`, `Título SEO` y `Descripción
meta`, porque esos tipos no tienen el checklist ampliado de la noticia.

El `Superadmin técnico` crea, desactiva y asigna usuarios y grupos, ejecuta el
bootstrap y atiende configuración técnica. No uses una cuenta superuser para
comprobar restricciones: el superuser omite los límites de los roles.

## Navegación pública

El sitio público comparte una navegación responsive entre la Home, el listado
de noticias, el detalle de cada noticia y las páginas institucionales. Incluye:

- `Inicio`;
- `Noticias`;
- las secciones principales existentes, que abren el listado filtrado por su
  slug;
- las páginas institucionales publicadas que tengan activa la opción nativa
  `mostrar en menús`.

Una página institucional que no exista, no esté publicada o no esté marcada
para menús no genera un enlace vacío en la navegación.

Las subsecciones no se añaden a este menú. Una noticia seleccionada sólo en una
subsección sí pertenece a su sección principal cuando se usa el filtro público.

## Páginas institucionales simples

Ruta para crear una página institucional:

```text
Páginas -> Inicio -> Añadir página hija -> Página institucional
```

La página usa el título nativo de Wagtail y añade estos campos:

- `Introducción`: resumen corto del propósito de la página;
- `Contenido`: texto enriquecido sencillo con negrita, cursiva, enlaces, H2,
  H3, listas numeradas o con viñetas y citas.

Para mostrarla en la navegación pública como Director/editor, abre `Asistente
SEO`, busca `Navegación y menús`, activa `mostrar en menús` y publícala. Esa
opción no está disponible para Curador SEO porque controla navegación, no SEO.
La página institucional no admite páginas hijas. No se crean páginas
institucionales ni contenido de forma automática.

## Verificación del sitio público con contenido real

La Home y el listado usan únicamente noticias reales publicadas y accesibles al
público. Para revisar el recorrido:

1. Publica una o dos noticias con datos ficticios y no sensibles.
2. Abre la Home y confirma que la noticia más reciente aparece como destacada y
   que las siguientes no la duplican.
3. Abre `/noticias/` y usa una sección de la navegación para revisar el filtro.
4. Abre el título de una noticia para revisar su detalle, cuerpo estructurado,
   imágenes y contenido de YouTube o Spotify cuando existan.

Si no hay noticias públicas, o una sección real no tiene resultados, la página
muestra un estado vacío. No se generan tarjetas ni datos de demostración.

## Buscador y filtros públicos de noticias

En el listado público de noticias (`/noticias/`) cualquier visitante puede usar
el buscador y los filtros sin iniciar sesión. El buscador revisa el título, el
contenido público y las etiquetas de las noticias publicadas; no muestra datos
internos de colaboradores ni información de privacidad.

El icono de lupa `Buscar noticias` está disponible en la navegación pública de
la Home, el listado, los detalles y las páginas institucionales. Lleva
directamente al buscador del listado de noticias.

Para encontrar una noticia:

1. Selecciona el icono `Buscar noticias`, abre `Noticias` desde la navegación
   pública o visita `/noticias/`.
2. Escribe una palabra o frase en `Buscar` y selecciona `Buscar`.
3. Si corresponde, limita el resultado con `Sección` o `Subsección`. Una
   sección principal incluye sus subsecciones; una subsección muestra sólo las
   noticias asignadas a esa subsección. Al elegir una sección, el selector de
   subsecciones muestra sólo las subsecciones de esa sección. Sin una sección
   elegida, las subsecciones siguen disponibles agrupadas por sección principal.
4. Desde el detalle de una noticia, selecciona una etiqueta para abrir el
   listado filtrado por esa etiqueta exacta.

Los filtros pueden combinarse. El enlace `Limpiar filtros` vuelve al listado
completo. Si se cambia la sección y la subsección anterior no pertenece a ella,
el selector limpia esa subsección. Si la dirección contiene una sección,
subsección o etiqueta que no existe, o combina filtros incompatibles, el sitio
explica el problema y ofrece volver a todas las noticias.

Junto al número de resultados hay un control para alternar entre `Mostrar más
antiguas primero` y `Mostrar más recientes primero`. Al usarlo se mantienen la
búsqueda y los filtros activos, y el listado vuelve a la primera página. Los
enlaces de paginación conservan la búsqueda, los filtros y el orden elegido.

Los resultados de una búsqueda se ordenan por relevancia de forma predeterminada.
Si se elige un orden cronológico explícito, se conservan las coincidencias de la
búsqueda y se muestran por fecha de publicación. El listado muestra diez
noticias por página y un estado vacío claro cuando no hay coincidencias.

## Secciones y subsecciones editoriales

La administración de la taxonomía está separada en dos rutas:

```text
Editorial -> Secciones
Editorial -> Subsecciones
```

La taxonomía tiene dos niveles. Una `sección principal` organiza una rama y una
`subsección` depende directamente de una sección principal. No se permiten
niveles adicionales.

En `Secciones` sólo aparecen las secciones principales. Sus campos son
`Nombre`, `Slug` y `Orden`; el formulario no muestra `Sección principal`. En
`Subsecciones` sólo aparecen las subsecciones. Sus campos son `Nombre`, `Slug`,
`Sección principal` y `Orden`. La sección principal es obligatoria y el selector
sólo ofrece secciones principales, nunca otras subsecciones.

El tipo queda fijo al crear la clasificación: una sección principal no puede
convertirse en subsección y una subsección no puede convertirse en sección
principal. Sí puedes mover una subsección a otra sección principal desde
`Editorial -> Subsecciones`. `Orden` organiza cada grupo de elementos hermanos.

Las secciones principales iniciales son:

- Política
- Cultura
- Medio Ambiente
- Problemáticas Sociales
- Columnas
- Entrevistas

La lista inicial de subsecciones es provisional y editable; sirve para validar
el flujo editorial y no reemplaza la definición institucional definitiva. No
se puede eliminar una clasificación que contenga subsecciones o esté asociada a
noticias actuales o históricas.

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
- Imagen destacada
- Contenido
- Secciones y subsecciones
- Cobertura
- Fecha de publicación
- Etiquetas
- Colegio
- Colaboradores internos
- Firma pública
- Privacidad de menores

La ubicación del colegio describe dónde está la institución educativa asociada.
La cobertura editorial describe el territorio sobre el que trata la noticia.
Pueden coincidir, pero no son el mismo dato.

`Secciones y subsecciones` muestra un árbol compacto de checkboxes. El control
de cada rama sólo muestra u oculta sus subsecciones: expandir `Cultura` no la
selecciona. Puedes elegir una subsección sin marcar su sección principal,
marcar sólo una sección principal o combinar varias secciones y subsecciones.
Marcar un elemento no marca automáticamente ningún padre ni hijo.

Guardar un borrador sin clasificación está permitido. Antes de publicar,
programar o completar el envío editorial, selecciona al menos una sección o
subsección. Al reabrir la noticia se conservan exactamente las selecciones
explícitas y las ramas que las contienen aparecen abiertas.

En el detalle público, una subsección se presenta con un path como `Cultura ›
Música`. Los paths legibles aparecen una sola vez, en la clasificación roja
superior. Si también seleccionaste `Cultura`, el detalle no repite una etiqueta
redundante de la misma rama ni añade una fila inferior de clasificación. La
Home, las tarjetas y el listado mantienen su diseño compacto y muestran
únicamente las secciones principales efectivas.

`Resumen` ya no forma parte del modelo ni del flujo editorial de una noticia.
La Home, el listado, las tarjetas y el detalle no fabrican una bajada desde
`Contenido`. Si se necesita una descripción para buscadores o redes, se escribe
de forma explícita en `Descripción meta` o `Descripción para redes sociales`
dentro de `Asistente SEO`.

## Imágenes y datos editoriales por uso

En la pestaña `Edición de la noticia`, `Imagen destacada` aparece
inmediatamente antes de la tarjeta `Contenido`. Esta imagen se usa en la
portada, el listado, las tarjetas, el detalle de la noticia y como fallback
social. Junto a la imagen se completan:

- `Pie de foto`: contexto visible que se muestra en el detalle público;
- `Texto alternativo`: descripción contextual para el atributo `alt`;
- `Crédito de imagen`: fuente o autoría pública opcional.

La ayuda de edición funciona igual en la imagen destacada, las imágenes del
cuerpo y la imagen social: al comenzar, el pie de foto se copia al texto
alternativo. Puedes personalizar el texto alternativo; después de hacerlo, los
cambios posteriores del pie ya no lo sobrescriben. Al reabrir una noticia, la
sincronización continúa sólo si el texto alternativo está vacío o todavía es
igual al pie.

La imagen destacada de las tarjetas usa el texto alternativo, pero no repite el
pie ni el crédito. Una noticia histórica puede seguir mostrándose aunque todavía
no tenga estos nuevos datos; en ese caso no se fabrica un pie visible ni se usa
automáticamente la descripción global del archivo como texto alternativo.

La biblioteca de imágenes y la noticia guardan información distinta. La pantalla
`Imágenes`, y el enlace `Editar esta imagen`, abren los datos generales del
archivo: allí viven su título, descripción, etiquetas, punto focal y usos. Estos
datos sirven para administrar y reutilizar el archivo, pero no reemplazan el
pie, el texto alternativo ni el crédito editorial del uso concreto en una
noticia. Si reutilizas el mismo archivo como destacada, dentro del cuerpo y como
imagen social, completa los datos editoriales adecuados en cada contexto.

El selector nativo ofrece `Búsqueda` para reutilizar un archivo y `Subir` para
incorporar uno nuevo. En la versión actual abre primero `Búsqueda`; selecciona
`Subir` cuando necesites cargar un archivo. La pestaña de búsqueda permanece
disponible en imagen destacada, imágenes del cuerpo e imagen social.

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

El título principal se escribe en `Título`, fuera del cuerpo. El campo
`Contenido` mantiene bloques separados y acepta:

- Párrafo
- Imagen
- Tabla
- Video de YouTube
- Audio o pódcast de Spotify

En el formulario normal, `Contenido` aparece como una tarjeta compacta. La
tarjeta muestra `Sin contenido` o `Con contenido`, sin contar bloques, y ofrece
`Abrir modo redacción`. Los bloques reales quedan ocultos detrás de la tarjeta,
pero continúan dentro del mismo formulario de Wagtail.

`Abrir modo redacción` abre una superficie que cubre el Admin completo. Su
encabezado muestra `Modo redacción`, el título actual de la noticia y `Volver`.
La superficie tiene scroll propio para artículos largos y presenta los bloques
en una columna documental centrada. `Volver` regresa al formulario sin guardar
automáticamente, conserva los cambios no guardados y devuelve el foco a la
acción de la tarjeta.

Los bloques siguen siendo unidades independientes. Los botones `+` permiten
insertarlos entre segmentos, y las acciones nativas para seleccionar, mover,
arrastrar, duplicar, eliminar y plegar continúan disponibles. Para no
interrumpir la escritura, esos controles se atenúan cuando el bloque está
inactivo y recuperan presencia con hover, selección, foco, teclado o error. Usa
`Tab` y `Shift+Tab` para recorrerlos; el foco visible no depende del mouse.

Para mantener una noticia fácil de reorganizar, crea bloques `Párrafo`
separados para los segmentos que necesites mover o entre los que quieras
insertar una imagen o multimedia. Cada bloque `Párrafo` sigue siendo RichText y
puede contener más de un párrafo cuando formen una sola unidad editorial.
Dentro del bloque pueden convivir encabezados H2, H3 y H4, negrita, cursiva,
enlaces, listas numeradas, listas con viñetas, citas, líneas horizontales y
enlaces a documentos del CMS. No existe un bloque de encabezado separado.

H2, H3 y H4 son formatos de párrafo completo, no estilos aplicados sólo a una
selección de palabras. Coloca el cursor en un párrafo independiente que contenga
únicamente el subtítulo y elige H2, H3 o H4. Separa párrafos y subtítulos con
saltos reales creados con `Enter`.

`Shift+Enter` crea un salto suave dentro del mismo párrafo. Algunos textos
pegados desde otras aplicaciones también pueden conservar saltos suaves. En
esos casos, varias líneas siguen siendo un único párrafo y aplicar H2, H3 o H4
puede transformar todas esas líneas. Si ocurre, reemplaza los saltos suaves por
saltos de párrafo con `Enter` antes de aplicar el formato.

Selecciona texto para mostrar la barra contextual nativa de formato del párrafo
activo. Al cambiar de párrafo, el formato se aplica sólo al editor que contiene
la selección; no existe una barra superior compartida. Pulsa `/` para abrir la
paleta de comandos y las acciones de bloque disponibles. La acción `Split
block` se encuentra en esa superficie y divide el bloque en la posición del
cursor; no aparece como botón permanente.

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

### Pegar una nota como bloques

El pegado inteligente funciona directamente dentro de `Modo redacción`; no hay
un botón ni una ventana adicional. Selecciona la nota en Word, Google Docs u
otro editor, cópiala con `Ctrl+C`, coloca el cursor o selecciona el bloque de
destino dentro de `Contenido` y usa `Ctrl+V`. No se selecciona, sube ni procesa
el archivo Word.

Cuando el portapapeles contiene varios párrafos, subtítulos, listas, tablas,
citas, separadores o varias líneas reales de texto plano, el sistema crea los
bloques automáticamente. Una notificación confirma cuántos bloques se pegaron
y avisa si algún elemento fue simplificado. No hay una revisión ni una
confirmación intermedia: comprueba el resultado dentro del mismo modo redacción
antes de guardar.

Si el cuerpo está vacío, los bloques se insertan al inicio. Si el cursor está en
un párrafo completamente vacío, ese párrafo se reemplaza. En un bloque con
contenido, la secuencia se inserta inmediatamente después; los bloques que ya
estaban a continuación conservan su orden. Si no se puede identificar un
destino, la secuencia se agrega al final. Un error de procesamiento no modifica
el contenido existente.

Una palabra, frase, URL o fragmento inline ordinario dentro de un párrafo usa el
pegado normal del editor, incluso si incluye negrita o cursiva. El pegado
inteligente no actúa dentro de campos de imagen, pie, texto alternativo,
crédito, selectores, inputs, áreas de texto ni celdas de tabla.

La conversión separa párrafos, subtítulos, listas continuas, citas, líneas
horizontales y tablas simples. Un H1 copiado se convierte en H2 porque el H1
público corresponde al `Título` de la noticia; H2 se conserva como H2, H3 como
H3 y H4, H5 o H6 se convierten en H4. Se conservan negrita, cursiva y enlaces
seguros. Colores, fuentes, tamaños, clases y otros estilos propios del documento
se descartan.

Cuando la aplicación de origen sólo entrega texto plano, cada línea no vacía
se convierte en un bloque `Párrafo` independiente. Las líneas vacías se omiten
y no se intenta adivinar cuáles son títulos. El ajuste visual automático de una
línea larga dentro de Word no crea un salto real y, por tanto, no divide el
párrafo. El texto plano no permite recuperar negritas, cursivas ni jerarquías
de títulos; aplica manualmente los formatos necesarios antes de publicar.

No se importan imágenes, formularios, iframes, scripts, contenido multimedia,
metadata del documento, autores, firmas, colaboradores, secciones, etiquetas ni
declaraciones de privacidad. Las imágenes descartadas deben añadirse
manualmente desde el CMS. Las listas anidadas, marcas de control de cambios,
código enriquecido y estructuras no compatibles se simplifican o descartan con
una advertencia.

Los espacios auxiliares, saltos iniciales o finales y párrafos vacíos que Word
añade alrededor del contenido no generan bloques ni líneas en blanco. Los
saltos internos reales, estilos inline compatibles y enlaces seguros sí se
conservan. Tras pegar, revisa el contenido y usa el guardado normal de Wagtail.

### Tablas

El bloque `Tabla` puede añadirse manualmente desde los controles `+` del
contenido. También se crea un bloque independiente por cada tabla HTML simple
detectada por el pegado inteligente. La importación conserva filas, columnas,
la descripción de tabla y las cabeceras de primera fila o primera columna
cuando el documento las identifica de forma inequívoca.

En `Modo redacción`, una tabla no seleccionada muestra únicamente la cuadrícula.
Haz clic en una celda o lleva el foco con el teclado para seleccionarla. La
tabla activa muestra `Encabezados de tabla`, todas sus opciones, `Descripción de
la tabla`, las ayudas y la barra de acciones. Al seleccionar otra tabla, la
anterior vuelve a mostrar sólo su cuadrícula. Una tabla con errores muestra
automáticamente sus controles. Este comportamiento contextual no cambia la
edición normal fuera de `Modo redacción`.

Las celdas se convierten siempre a texto seguro. Las continuaciones de celdas
combinadas se representan con celdas vacías para conservar el orden
rectangular. Las tablas anidadas se reducen a texto separado dentro de la celda
exterior. Las filas irregulares se completan con celdas vacías. Todos estos
casos muestran una advertencia para que revises el resultado. No se importan
estilos, imágenes, formularios, contenido multimedia, fórmulas ni HTML
enriquecido dentro de las celdas.

Los límites de una tabla son 50 filas, 20 columnas, 1000 celdas, 2000
caracteres por celda y 300 caracteres para la descripción. Durante una
importación, el contenido que exceda esos límites se recorta de forma segura y
se muestra una advertencia; la edición manual no permite guardar una tabla que
los supere.

En la noticia pública, la descripción y las cabeceras se muestran con semántica
de tabla. En pantallas estrechas, la tabla permite desplazamiento horizontal
dentro del cuerpo sin ampliar la página completa. Usa `Previsualizar` y
comprueba el texto descriptivo, las cabeceras y todos los datos antes de
publicar.

El editor actual no ofrece un control para anidar listas y `Tab` desplaza el
foco. La autoría de listas anidadas no aplica en esta interfaz. El análisis
aplana cualquier lista anidada importada a un solo nivel, conserva el texto en
orden y muestra una advertencia, sin añadir atajos propios.

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

En `Modo redacción`, el bloque `Imagen` se presenta como una figura compacta
dentro del flujo, con una previsualización proporcional de hasta unos 260 px de
alto. Cuando está inactivo prioriza la imagen, el pie y el crédito disponibles.
Al seleccionarlo muestra los controles para elegir o reemplazar la imagen y los
campos `Pie de foto`, `Texto alternativo` y `Crédito de imagen`. Un error
también despliega automáticamente esos controles. El modo no cambia la
validación ni convierte esos datos en campos sueltos.

La ayuda compartida de pie de foto y texto alternativo descrita en la sección de
imágenes también se aplica al crear bloques nuevos y al reabrir bloques
existentes del cuerpo.

Guardar como borrador permite dejar incompleta una imagen del cuerpo. Para
publicar, programar o enviar a workflow, la imagen, el pie de foto y el texto
alternativo deben estar completos; espacios en blanco no cuentan como contenido
efectivo.

`Video de YouTube` acepta URLs compatibles de YouTube. `Audio o pódcast de
Spotify` acepta URLs compatibles de Spotify. En `Modo redacción` se muestran
como tarjetas compactas con el proveedor y la URL; seleccionarlas revela su
campo editable. No cargan un embed grande ni reproducen contenido
automáticamente. Si una URL no pertenece al proveedor del bloque, la validación
la rechaza y revela el control con el error. Si una URL previamente válida deja
de resolverse como contenido multimedia público, la noticia muestra un enlace
a la URL original con una etiqueta del proveedor. No uses una inserción
multimedia genérica dentro de `Párrafo`.

Después de guardar y reabrir la noticia, los bloques existentes vuelven a
funcionar desde la misma tarjeta y superficie de redacción. Usa `Previsualizar`
para comprobar el resultado final: el modo redacción sólo afecta el Admin y no
cambia el detalle público.

## Borrador y publicación

Guardar como borrador conserva la noticia dentro de Wagtail Admin sin mostrarla
en la Home pública anónima.

Publicar la noticia mediante Wagtail la hace visible en la Home pública. Desde
la Home, el título de la noticia abre su página pública de detalle.

La publicación, programación o envío a workflow se bloquea cuando:

- falta una firma pública efectiva;
- existe una imagen destacada sin pie de foto o texto alternativo efectivo;
- una imagen del cuerpo no tiene imagen, pie de foto o texto alternativo
  efectivo;
- existe una imagen para redes sociales propia sin pie de foto o texto
  alternativo efectivo;
- `Contiene menores identificables` está marcado y no se confirmó la
  verificación de autorizaciones.

Cuando `Contenido` tiene un error, la tarjeta muestra:

```text
El contenido de la noticia contiene errores. Abre el modo redacción para revisarlos.
```

La acción cambia a `Revisar errores`. Al abrirla, la superficie muestra
`Revisa los bloques marcados con errores.`, despliega el bloque afectado y lleva
el foco al primer control inválido cuando es seguro. Los enlaces del resumen
general de errores abren esta misma ruta; no envían a contenido oculto.

## Workflow editorial MVP

El camino operativo recomendado es:

```text
Borrador
→ Revisión SEO
→ Revisión editorial final
→ publicación automática
```

Como Director/editor:

1. Completa contenido, firma pública, privacidad, imágenes y datos necesarios.
2. Usa `Guardar borrador` mientras el trabajo esté incompleto.
3. Cuando las validaciones estén completas, elige `Enviar a Revisión
   editorial`.
4. Después de la aprobación SEO, abre la tarea `Revisión editorial final`.
5. Elige `Aprobar y Publicar` o `Aprobar con comentario y Publicar`. La
   aprobación de esta última tarea termina el workflow y publica
   automáticamente la revisión nativa.

Como Curador SEO, abre la tarea `Revisión SEO` desde el panel o el informe de
tareas, revisa los campos permitidos y elige:

- `Solicitar cambios` para devolver el contenido al Director/editor con un
  comentario; o
- `Aprobar` / `Aprobar con comentario` para avanzar a `Revisión editorial
  final`.

Un Director/editor conserva el botón `Publicar` como override autorizado del
MVP. Úsalo sólo cuando la operación requiera omitir el recorrido recomendado;
no elimina ninguna validación de créditos públicos, privacidad o metadata de
imágenes. Curador SEO nunca tiene publicación directa.

En `Revisión editorial final`, las acciones visibles tienen propósitos
distintos: `Publicar` es el override directo; `Aprobar y Publicar` y `Aprobar
con comentario y Publicar` son el cierre normal del workflow. También pueden
aparecer `Cancelar flujo de trabajo`, `Solicitar cambios` y `Guardar borrador`.

El workflow está asignado a `Inicio` y, por herencia nativa del árbol, afecta a
la propia Home, las noticias y las páginas institucionales debajo de ella. En
las páginas sin Asistente SEO ampliado, Curador SEO revisa los tres campos SEO
nativos y puede aprobar o solicitar cambios sin acceder al contenido.

Una cuenta no-superuser puede pertenecer a ambos grupos y completar las dos
tareas. Esa cuenta acumula permisos y no sirve para demostrar el aislamiento de
Curador SEO.

## Cuenta y contraseña

En el menú de la cuenta, usa `Cambiar contraseña` para reemplazar tu propia
contraseña. En el primer acceso, cambia inmediatamente la contraseña temporal
que el superadmin te entregó por un canal privado. Este MVP no impone todavía
un bloqueo técnico que obligue a cambiarla en el primer inicio de sesión.

Si una persona olvida la contraseña mientras el correo saliente no está
operativo, debe pedir al superadmin un restablecimiento administrativo. No
envíes contraseñas por canales públicos ni las guardes en el repositorio.

## Asistente SEO

Para Director/editor, cada noticia muestra `Edición de la noticia` y `Asistente
SEO`. Para Curador SEO durante su tarea activa, sólo se muestra `Asistente SEO`.
La configuración de página de Wagtail permanece fuera de la superficie SEO y
no queda editable para Curador SEO.

La pestaña `Asistente SEO` reutiliza los
campos nativos de Wagtail para la URL, el título SEO y la descripción meta, y
añade herramientas editoriales para revisar la noticia antes de publicarla.

La pestaña comienza directamente con `Configuración SEO`. Curador SEO puede
usar la acción nativa `Vista previa` de Wagtail, incluida su vista dividida o la
apertura en otra pestaña, para revisar el contenido completo de la noticia. La
vista previa no amplía los campos editables: cuerpo, taxonomía, colaboradores,
privacidad y créditos continúan fuera de la superficie del rol.

En la Home y las páginas institucionales, `Contexto de la página — solo
lectura` muestra el título y la misma acción de previsualización. Curador SEO
continúa limitado a `Slug de la URL`, `Título SEO` y `Descripción meta`.

El Asistente SEO es una ayuda formativa. Sus recomendaciones y su semáforo no
bloquean el guardado, la programación, el envío a workflow ni la publicación.
Después de guardar correctamente un borrador o una actualización desde esta
pestaña, la página de edición vuelve a abrir `Asistente SEO`. Si hay errores de
validación, Wagtail conserva su comportamiento normal y abre la superficie que
corresponda al error.

### Configuración SEO

Los campos principales son:

- `Slug de la URL`: parte final de la dirección pública de la noticia.
- `Título SEO`: texto usado en la etiqueta `<title>` y como título de buscador.
- `Descripción meta`: resumen preparado para buscadores.
- `Frase clave principal`: frase central que se quiere trabajar.
- `Frases clave relacionadas`: hasta cuatro expresiones opcionales que también
  describen el tema.

La frase principal puede quedar vacía en un borrador. Mientras falte, el
análisis aparece incompleto. Las relacionadas se pueden añadir, eliminar y
reordenar. No se permite repetir la principal ni otra relacionada aunque la
diferencia sea sólo de mayúsculas, tildes, Unicode o espacios. Una fila vacía
no cuenta para el máximo.

El análisis distingue una `Coincidencia exacta` de una `Variante flexiva`. La
coincidencia exacta conserva la comparación sin diferencias de mayúsculas,
espacios repetidos ni tildes. La variante flexiva usa una herramienta
lingüística local para reconocer, de forma conservadora, cambios cercanos como
`investigación escolar` y `investigaciones escolares`. No busca sinónimos, no
reordena palabras y no considera equivalentes `investigación escolar` y
`estudio educativo`.

El contador del título SEO usa estos rangos orientativos:

- 30 a 60 caracteres: bueno.
- 1 a 29 o 61 a 70: necesita revisión.
- vacío o más de 70: problema.

El contador de la descripción meta usa estos rangos:

- 120 a 160 caracteres: bueno.
- 1 a 119 o 161 a 180: necesita revisión.
- vacía o más de 180: problema.

Los rangos se basan en caracteres y son una aproximación editorial. La vista
previa no reproduce exactamente el ancho que puede usar un buscador real.

### Vista previa en buscador

La vista previa muestra:

- el título SEO o, como fallback, el título de la noticia;
- la URL canonical disponible o una representación del slug;
- la descripción meta cuando tiene contenido.

Si `Descripción meta` está vacía, la metadata pública omite la descripción. No
se deriva un extracto desde `Contenido`. El checklist recomienda completar la
descripción meta de forma explícita.

El título, la descripción, el slug y la URL canonical actualizan esta vista
previa mientras se editan. El análisis completo del cuerpo y de las frases
clave no se ejecuta en cada pulsación: se recalcula en el servidor después de
guardar o volver a abrir la noticia. Esto incluye los cálculos SEO, lingüísticos
y de legibilidad del contenido estructurado.

### Configuración y vista previa social

Los campos sociales son:

- `Título para redes sociales`;
- `Descripción para redes sociales`;
- `Imagen para redes sociales`;
- `Pie de foto`, `Texto alternativo` y `Crédito de imagen` para ese uso social.

La imagen social y sus datos editoriales permanecen dentro de `Asistente SEO`.
Si eliges una imagen social propia, el pie y el texto alternativo son
obligatorios para la validación completa; el crédito es opcional. El pie social
se conserva como contexto editorial, pero la imagen social no se muestra como
contenido visible en el detalle por defecto.

Si quedan vacíos, se aplican estos fallbacks:

```text
Título social
→ título SEO
→ título de la noticia

Descripción social
→ descripción meta
→ se omite si ambas están vacías

Imagen social
→ imagen destacada

Texto alternativo social
→ texto alternativo de la imagen destacada cuando opera ese fallback
```

La vista previa es conceptual. No representa exactamente la interfaz de una red
social ni publica contenido automáticamente. Los cambios de texto se actualizan
en la vista previa durante la edición; la imagen elegida queda reflejada de
forma autoritativa después de guardar o recargar.

### Análisis SEO

El análisis revisa de forma determinística:

- presencia de la frase clave principal;
- frase clave en título SEO, slug, descripción meta, introducción, subtítulos y
  cuerpo;
- repetición evidente de la frase clave;
- longitud del título SEO y de la descripción meta;
- extensión del cuerpo;
- imagen destacada y su metadata contextual;
- imagen social efectiva y su metadata contextual;
- texto alternativo de imágenes del cuerpo;
- presencia de enlaces internos y externos.

Un artículo de 300 palabras o más obtiene el resultado recomendado de extensión.
Entre 150 y 299 palabras aparece una advertencia; con menos de 150 aparece un
problema. No tener enlaces se muestra como recomendación, no como obligación de
añadir enlaces irrelevantes.

Cuando no hay subtítulos, imágenes del cuerpo o texto suficiente para una
comprobación, el resultado puede mostrarse como `No aplica`.

### Análisis de frases clave

`Análisis de la frase principal` conserva todos los resultados exactos y añade
resultados orientativos para variantes flexivas, la introducción y la
distribución. La introducción corresponde a los primeros 100 tokens
significativos del contenido. La distribución se aplica a partir de 300
palabras significativas y divide aproximadamente el cuerpo en tres zonas.

`Análisis de frases relacionadas` presenta un grupo independiente por cada
frase, en el orden editorial. Cada grupo explica presencia, ubicaciones y
distribución. Las ubicaciones distinguen título público o SEO, descripción,
introducción, subtítulos y cuerpo. Las evidencias son fragmentos breves: una
predicción flexiva nunca se presenta como coincidencia exacta.

Las relacionadas, las variantes flexivas y la distribución nueva no cambian
el estado general `Incompleto`, `Necesita mejoras` o `Bueno`. Son orientación
adicional y no una puntuación lingüística global.

Si la herramienta lingüística local no está disponible, aparece `El análisis
lingüístico avanzado no está disponible. Revisa la configuración del servidor.`
Los resultados exactos existentes continúan visibles y se puede guardar,
enviar a workflow o publicar según los permisos habituales. Si el contenido
supera el límite técnico configurado, aparece `El texto es demasiado extenso
para el análisis lingüístico configurado.`; el texto no se trunca
silenciosamente.

### Legibilidad en español

La tarjeta `Legibilidad` conserva las heurísticas básicas que ya forman parte
del estado general:

- confirma que exista prosa;
- advierte por párrafos de más de 150 palabras y marca como problema los de más
  de 250;
- considera larga una oración de más de 30 palabras;
- recomienda subtítulos en artículos de 300 palabras o más;
- advierte cuando una sección continua supera 300 palabras y marca como
  problema una sección de más de 500.

La separación automática de oraciones puede no interpretar perfectamente
abreviaturas o puntuación inusual. Los resultados son recomendaciones
editoriales, no una certificación lingüística ni una fórmula definitiva de
calidad en español.

La tarjeta separada `Legibilidad avanzada` reutiliza el análisis lingüístico
local para orientar una revisión más detallada. Sus ocho resultados no cambian
el estado general `Incompleto`, `Necesita mejoras` o `Bueno`. Se calculan en el
servidor después de guardar o volver a abrir la noticia; no se actualizan por
cada pulsación y no corrigen ni reescriben el contenido automáticamente.

Las métricas avanzadas usan sólo la prosa visible de párrafos, listas y citas
del cuerpo. Los subtítulos sirven como límites editoriales, pero sus palabras
no entran en los cálculos. Tampoco se analizan para estas métricas el título,
la metadata SEO, las tablas, las imágenes, los pies, los créditos, la
taxonomía ni datos internos. Una oración nunca se une con texto de otro bloque.

Los resultados aparecen en este orden:

1. `Oraciones extensas con evidencia`: localiza oraciones de más de 30
   palabras. Hasta 25 % del total aparece como `Correcto`; una proporción mayor
   aparece como `Por mejorar`. El porcentaje visible se trunca al entero
   inferior y las evidencias más extensas aparecen primero.
2. `Comienzos consecutivos`: compara los dos primeros lemas de contenido y
   señala sólo secuencias de tres o más oraciones con la misma firma. Dos
   comienzos semejantes no se marcan.
3. `Uso de conectores`: cuenta una sola vez cada oración que contiene al menos
   un conector del léxico del proyecto. Con menos de cinco oraciones muestra
   `No aplica`; menos de 10 % es `Por mejorar`, desde 10 % y menos de 20 % es
   `Informativo`, y desde 20 % es `Correcto`. Una proporción alta no garantiza
   mejor escritura ni implica que deban insertarse conectores mecánicamente.
4. `Pasiva perifrástica`: busca de forma conservadora una forma de `ser` unida
   sintácticamente a un participio verbal. No cuenta construcciones con
   `estar`, usos con `se` ni adjetivos detectados sin evidencia verbal. Una
   ocurrencia o una proporción menor de 10 % es informativa; dos o más y al
   menos 10 % aparecen como `Por mejorar`.
5. `Complejidad sintáctica`: considera compleja una oración con tres o más
   cabezas de cláusula estimadas. Con menos de tres oraciones muestra `No
   aplica`; una proporción de hasta 20 % es informativa y una mayor aparece
   como `Por mejorar`. No es un análisis gramatical exhaustivo.
6. `Densidad léxica`: desde 50 palabras muestra, como dato `Informativo`, la
   proporción de adjetivos, adverbios, sustantivos, nombres propios y verbos.
   No clasifica el valor como bueno o malo porque depende del género, la edad,
   el estilo y el propósito.
7. `Diversidad léxica`: desde 50 tokens de contenido muestra MATTR con una
   ventana fija de 50 lemas y tres decimales. Es `Informativo` y no genera
   sugerencias automáticas de sinónimos.
8. `Flesch-Szigriszt e INFLESZ`: se calcula desde 100 palabras y tres
   oraciones. Muestra palabras, oraciones, sílabas, un decimal del índice y la
   banda `Muy difícil`, `Algo difícil`, `Normal`, `Bastante fácil` o `Muy
   fácil`. Un valor inferior a 55 aparece como `Por mejorar`; desde 55 aparece
   como `Correcto`. Es un índice orientativo de esta métrica, no una puntuación
   del artículo ni del SEO, y no se limita artificialmente al rango 0–100.

Cada resultado explica su métrica y puede mostrar hasta tres fragmentos con el
tipo, ordinal y referencia del bloque. La evidencia es sólo una ayuda para
localizar el pasaje: no se guarda como dato de la noticia ni certifica calidad,
comprensión, veracidad, justicia o relevancia.

Si el pipeline lingüístico no está disponible, falla durante esa respuesta o
el texto supera el límite configurado, los ocho resultados avanzados muestran
`No disponible`; la tarjeta básica, el análisis SEO, el guardado y el workflow
continúan funcionando. Si falla únicamente la silabación local `es_ES`, los
primeros siete resultados continúan y sólo `Flesch-Szigriszt e INFLESZ`
muestra `No disponible`. Ninguno de estos procesos descarga diccionarios ni
envía el texto a un servicio externo.

### Estado general

El semáforo tiene tres estados:

- `Bueno`: todas las comprobaciones aplicables están bien.
- `Necesita mejoras`: los datos básicos existen, pero quedan advertencias o
  problemas.
- `Incompleto`: falta la frase clave, el título SEO, la descripción meta o el
  texto del artículo.

El semáforo no garantiza posicionamiento ni elegibilidad para resultados
enriquecidos.

### Indexación y URL canonical

`Excluir de los resultados de búsqueda` añade una directiva pública
`noindex, follow` a esa noticia. La página sigue siendo accesible y los
buscadores pueden rastrearla para leer la directiva. Una noticia noindex no se
incluye en el sitemap.

El entorno completo también puede estar configurado con noindex. Cuando ese
modo conservador está activo, tanto la Home como todas las noticias emiten
noindex y quedan fuera del sitemap, aunque la marca individual de una noticia
esté desactivada.

`URL canonical` indica la versión principal de la noticia:

- vacía: usa la propia URL pública;
- igual a la URL pública: canonical propia;
- diferente: publica la URL configurada como canonical y omite la URL local del
  sitemap.

No uses canonical para ocultar contenido privado ni como sustituto de noindex.
Debe ser una URL HTTP o HTTPS completa y no puede contener un fragmento `#`.

### Navegación y menús

`Navegación y menús` contiene la opción nativa `mostrar en menús`. Esta opción
sirve para menús generados por el sitio y no participa en el análisis ni en el
semáforo SEO. Sólo Director/editor puede modificarla.

### Metadata pública

La página pública de una noticia genera:

- título y descripción;
- canonical;
- directiva robots;
- Open Graph;
- tarjeta básica para Twitter/X;
- JSON-LD `NewsArticle`.

Los autores de JSON-LD salen exclusivamente de las firmas públicas, respetando
su orden y omitiendo valores vacíos. No se usan colaboradores internos, nombres
internos de menores, franjas de edad ni marcas de privacidad.

Como una firma pública puede representar a una persona o a un equipo y esta
versión no guarda ese tipo, los autores JSON-LD se publican sólo con su nombre,
sin inferir `Person` u `Organization`. La herramienta no promete elegibilidad
para resultados enriquecidos.

### Acciones públicas para compartir

El detalle público de una noticia publicada muestra `Compartir esta noticia`
después del cuerpo y antes de las etiquetas. Las acciones disponibles son
`Compartir`, `WhatsApp`, `X`, `Facebook`, `Correo` y `Copiar enlace`.

Todas usan la URL canonical efectiva. Si `URL canonical` está vacía, se comparte
la URL pública propia; si contiene una canonical externa, se comparte esa URL
externa. La marca `Excluir de los resultados de búsqueda` no oculta las acciones,
pero estas no aparecen en la vista previa de un borrador.

`Compartir` aparece únicamente cuando el navegador y el dispositivo admiten el
selector nativo para el contenido de la noticia. Las opciones del selector
dependen de las aplicaciones disponibles; el sitio no promete una aplicación
concreta ni la creación directa de una historia. Cuando Web Share no es
compatible, sólo se muestran las demás acciones que sí pueden funcionar.

`Copiar enlace` usa el portapapeles del navegador. El resultado se muestra en
una notificación temporal que puede cerrarse. Cuando la copia automática no es
posible, la notificación incluye un campo de solo lectura para seleccionar y
copiar la canonical de forma manual, y permanece disponible hasta pulsar
`Cerrar`.

School Newsroom prepara los enlaces y abre el compositor o manejador disponible,
pero no puede confirmar si la persona terminó una publicación, un mensaje o un
correo en una plataforma externa.

Los endpoints técnicos son:

```text
/sitemap.xml
/robots.txt
```

`robots.txt` permite el rastreo e indica la dirección del sitemap. No se usa
para ocultar páginas noindex.

## Limitaciones actuales

- El workflow MVP usa las capacidades nativas de Wagtail y es el camino
  recomendado, pero Director/editor conserva publicación directa autorizada.
- No existe cambio obligatorio de contraseña ni bloqueo técnico en el primer
  acceso.
- No hay correo saliente/transaccional operativo ni recuperación operacional
  de contraseña por correo.
- No hay cuentas de estudiantes, docentes, monitores ni tutores todavía.
- No hay responsabilidades individuales por fotografía, investigación,
  redacción u otras labores todavía.
- No hay perfil público reusable de autor todavía.
- No hay tipos persistidos de firma pública todavía.
- No hay carga ni seguimiento individual de documentos de autorización todavía.
- Provincia y Distrito no se validan todavía contra datos geográficos oficiales.
- No hay análisis de sinónimos, variantes gramaticales, múltiples frases clave
  ni inteligencia artificial dentro del Asistente SEO.
- No hay integración con Search Console, Google News, analytics ni publicación
  automática en redes sociales.
- No hay gestión de redirecciones ni una vista SEO dedicada separada del editor
  nativo con panels condicionados por permiso.
- No hay análisis automático de rostros, voces, proveedores externos ni datos
  personales dentro de imágenes, video o audio.
- No existe un sistema de gestión de talleres, inscripciones o agenda.
- Las páginas institucionales son contenido simple; no incluyen gestión de
  equipos, constructor de páginas, formularios ni flujos institucionales
  avanzados.
