# Wagtail MVP Access Runbook

This is the canonical operations procedure for adult Wagtail CMS access in the
MVP. The technical superuser owns user lifecycle, group assignment, and access
recovery. Human users and passwords are never created by repository bootstrap
code.

## Access model

| Capability | Technical superuser | Director/editor | Curador SEO |
| --- | --- | --- | --- |
| Enter Wagtail Admin | Yes | Yes | Yes |
| Administer users, groups, permissions | Yes | No | No |
| Create/edit pages below `Inicio` | Yes | Yes | Only the active workflow task |
| Edit full news or institutional content | Yes | Yes | No |
| Edit allowed SEO fields | Yes | Yes | Yes |
| Edit `show_in_menus` or page properties | Yes | Yes | No |
| Manage editorial snippets, including internal minor records | Yes | Yes | No |
| Add/change/select images | Yes | Yes | Select existing images only |
| Add/change/select documents | Yes | Yes | No |
| Approve `Revisión SEO` | Yes | Through Curador SEO membership | Yes |
| Approve `Revisión editorial final` | Yes | Yes | No |
| Publish directly | Yes | Yes, authorized MVP override | No |

The group permissions are cumulative. A non-superuser in both groups can
complete both workflow tasks and has the full Director/editor surface. Do not
use that combined account to validate Curador SEO isolation.

The implementation does not claim row-level isolation by school, district,
province, or territory. Director/editor access to internal minor-contributor
records exists only because that role carries editorial responsibility.

## Apply migrations and bootstrap access

Start the Docker-first runtime and apply migrations before bootstrap:

```bash
make up
make migrate
```

From the host, with the `web` service running:

```bash
docker compose exec web python manage.py bootstrap_mvp_access
```

Inside the Dev Container:

```bash
python manage.py bootstrap_mvp_access
```

The command creates or updates these owned objects:

```text
Group: Director/editor
Group: Curador SEO
Task: Revisión SEO
Task: Revisión editorial final
Workflow: Revisión editorial
Assignment: Inicio subtree
```

The workflow is named `Revisión editorial`. Migration
`0009_reconcile_mvp_access` removes only the obsolete exact-name groups
`Moderadores` and `Editores` plus the exact-name task, workflow, and assignment
`Aprobación de moderadores`. It stops with an actionable error instead of
deleting when either group still has users or when any unexpected workflow,
task, state, assignment, or group dependency exists. Unrelated access objects
are preserved. The same migration renames `Revisión editorial MVP` in place so
its database identity and history remain intact.

Run the command again after changing deployment data or configuration. It is
idempotent: it updates the two owned groups and workflow objects rather than
duplicating them. It also removes ad hoc global, page, or collection permissions
from the two owned groups and restores the reviewed MVP matrix. Do not add
manual permissions directly to these groups.

## Assign existing users from the command line

The command accepts existing login names and never creates a user:

```bash
python manage.py bootstrap_mvp_access --director director_login
python manage.py bootstrap_mvp_access --seo-curator seo_login
python manage.py bootstrap_mvp_access --combined-user combined_login
```

Each option may be repeated. The combined option adds both groups. If a login
does not exist, the transaction fails and no partial bootstrap or assignment is
kept. No password is accepted or printed.

## Create users in Wagtail Admin

Use the existing technical superuser.

1. Open Wagtail Admin and go to `Configuración` -> `Usuarios`.
2. Select `Añadir un usuario`.
3. Enter a unique `Nombre de usuario`, fictional or work-approved `Nombre`,
   `Apellidos`, and `Correo electrónico` as appropriate for the environment.
4. Leave `Administrador` unselected. Selecting it creates a superuser-equivalent
   account and invalidates role testing.
5. Under `Grupos`, select exactly `Director/editor`, exactly `Curador SEO`, or
   both only for the documented single-person operation case.
6. Enter a unique temporary value in `Contraseña` and `Confirmación de
   contraseña`. Do not use a repository example as a real password.
7. Save the user.
8. Deliver the temporary password privately and ask the user to sign in and use
   `Cuenta` -> `Cambiar contraseña` immediately.

This MVP does not enforce a first-login password-change lock. The immediate
change is an operational requirement, not a technical gate.

### Create a Director/editor

Follow the general creation steps, leave `Administrador` unselected, and choose
only `Director/editor` under `Grupos`. The result must be an active
non-superuser.

### Create a Curador SEO

Follow the general creation steps, leave `Administrador` unselected, and choose
only `Curador SEO` under `Grupos`. Use a separate account for isolation testing.

### Create a combined non-superuser

Follow the general creation steps, leave `Administrador` unselected, and choose
both `Director/editor` and `Curador SEO`. This is allowed for a one-person
operation, but the account accumulates both roles.

## Change roles, deactivate access, or reset a password

Go to `Configuración` -> `Usuarios`, open the user, and use the existing user
form:

- To add or remove a role, change only the `Grupos` selection and save. Do not
  grant individual permissions or select unrelated historical groups.
- To suspend access without deleting history, clear `Activo` and save.
- To restore access, reselect `Activo`, confirm the intended groups, and save.
- To reset a forgotten password while outgoing email is unavailable, enter a
  new temporary value in `Contraseña` and `Confirmación de contraseña`, save,
  deliver it privately, and require an immediate voluntary change through
  `Cuenta` -> `Cambiar contraseña`.

Prefer deactivation to deletion so editorial and workflow history remains
attributable. Never store passwords in source control, tickets, shared UAT
notes, or command history.

## Maintain the existing technical superuser

To review or update the superuser's basic account data, sign in as that user,
open `Configuración` -> `Usuarios`, select the same account, update `Nombre`,
`Apellidos`, `Correo electrónico`, or `Nombre de usuario` as required, and save.
Confirm that `Administrador` remains selected only for the intended technical
superuser.

To change the superuser's own password, use `Cuenta` -> `Cambiar contraseña`,
enter the current password and the new private password requested by the UI,
and save. Do not use the role bootstrap to change user data or passwords.

## Workflow operation

The workflow order is native and fixed for the MVP:

```text
Borrador
-> Revisión SEO (Curador SEO)
-> Revisión editorial final (Director/editor)
-> native publication on final approval
```

Director/editor uses `Guardar borrador`, then `Enviar a Revisión editorial`
once the existing publication validations pass. Curador SEO can use `Solicitar
cambios`, `Aprobar`, or `Aprobar con comentario` on the SEO task. Both
`Solicitar cambios` and approval to the next task return the curator to the
authorized dashboard after completing successfully. At final review,
Director/editor uses `Aprobar y Publicar` or `Aprobar con comentario y
Publicar`. Wagtail completes the workflow and publishes the revision through
its native workflow finish action.

Director/editor also retains direct `Publicar` permission as an authorized MVP
override. The workflow is the recommended operating path, not absolute
enforcement against that role. Curador SEO has no direct publish permission.

The same `Inicio` subtree assignment also places `HomePage` and
`InstitutionalPage` through both tasks. Curador SEO sees the three native SEO
fields on those page types and never sees their content, menu, or property
fields. On `NewsPage`, the role sees the extended `Asistente SEO` surface.

## Server-side SEO boundary

Wagtail panel permissions remove unauthorized tabs and panels. Wagtail's
permission-aware admin form removes unauthorized fields before binding POST
data. Child formsets for public credits, internal contributors, and comments are
also absent for users without the full editorial-surface permission.

Consequently, a crafted POST from Curador SEO cannot change `title`, `summary`,
`body`, privacy flags, `show_in_menus`, internal contributors, public credits,
or page properties. This boundary does not rely on CSS or JavaScript. The SEO
role can change:

- `slug`, `seo_title`, and `search_description` on every affected page type;
- `focus_keyphrase`, social text/image and contextual social metadata,
  `canonical_url`, and `seo_noindex` on news pages.

The chooser-only image collection permission supports selecting an existing
social image without granting image upload, change, or deletion.

The SEO tab starts with a server-rendered read-only context. For news it is
labelled `Contexto de la noticia — solo lectura` and includes the public title,
section, date, summary, faithful body rendering, featured image with contextual
public metadata, public credits, and `Previsualizar borrador completo`. It does
not expose internal contributors, age bands, privacy declarations, or
authorization flags. Home and institutional pages show `Contexto de la página
— solo lectura` with their title and the same explicit draft-preview action.
These panels contain no form controls and do not expand the POST field set.

## Email recovery prerequisites

Outgoing application email is not operational in this ticket. Before
email-based password recovery can be relied on, a later deployment task must:

1. configure a real Django email backend, host, port, authentication secret,
   TLS/SSL behavior, and default sender through deployment secrets;
2. configure the correct external Wagtail Admin base URL;
3. verify password-reset URLs and templates for the deployed hostname;
4. validate sender-domain authentication and delivery in the target
   environment;
5. test expiry, one-time use, inactive-user behavior, and support procedures.

Until that work exists, use the administrative reset procedure above. Do not
claim that recovery email works merely because Django contains password-reset
components.

## UAT del mantenedor

Usa sólo los valores ficticios de esta sección. No copies una contraseña real,
un nombre real de menor ni una imagen real. Registra por separado `Resultado
obtenido`, `Aprobado/No aprobado` y evidencia; los resultados esperados de este
documento no cuentan como ejecución.

### Precondiciones y datos ficticios fijos

Precondiciones:

1. `make up` está activo y el Admin responde en `http://localhost:8000/admin/`.
2. Existe un superusuario técnico conocido por el mantenedor.
3. Hay dos sesiones separadas, una para `uat_director` y otra para `uat_seo`.
4. Las contraseñas temporales se acuerdan por un canal privado y no se anotan
   aquí, en el ticket ni en el historial de comandos.
5. La fecha UAT se puede sustituir por la fecha de ejecución, pero debe usarse
   el mismo valor en el campo y en la evidencia.

Cuentas:

| Campo | Director/editor | Curador SEO |
| --- | --- | --- |
| `Nombre de usuario` | `uat_director` | `uat_seo` |
| `Nombre` | `Directora` | `Curadora` |
| `Apellidos` | `Ficticia UAT` | `Ficticia UAT` |
| `Correo electrónico` | `uat_director@example.invalid` | `uat_seo@example.invalid` |
| `Administrador` | desmarcado | desmarcado |
| `Activo` | marcado | marcado |
| `Grupos` | sólo `Director/editor` | sólo `Curador SEO` |

Datos editoriales internos:

```text
Colegio / Nombre: Colegio Horizonte Ficticio
Colegio / Provincia: Arequipa
Colegio / Distrito: Cercado

Grupo de colaboradores / Nombre: Taller de Periodismo Horizonte
Grupo de colaboradores / Colegio: Colegio Horizonte Ficticio

Colaborador menor / Nombre interno: Ana Ficticia UAT
Colaborador menor / Grupo: Taller de Periodismo Horizonte
Colaborador menor / Franja de edad: Menor de 14 años
```

Archivos de prueba: usa dos GIF/JPG sin personas reales, llamados
`uat-portada-ficticia.gif` y `uat-social-ficticia.gif`. Al cargarlos en
`Imágenes`, usa respectivamente `Portada ficticia UAT` e `Imagen social
ficticia UAT` como título del activo.

Noticia de publicación directa:

```text
Título: UAT directa: biblioteca escolar abre un rincón de lectura
Fecha de publicación: 15/07/2026
Resumen: La biblioteca ficticia habilitó un espacio de lectura para la comunidad educativa.
Contenido: La comunidad del Colegio Horizonte Ficticio inauguró un rincón de lectura con libros de prueba y actividades editoriales simuladas.
Firma pública: Redacción escolar ficticia UAT
Sección: Política
Colegio: Colegio Horizonte Ficticio
Provincia de cobertura: Arequipa
Distrito de cobertura: Cercado
Etiquetas: dejar vacío
Contiene menores identificables: desmarcado
Confirmo que se verificaron las autorizaciones requeridas...: desmarcado
Contenido sensible: desmarcado

Imagen destacada: uat-portada-ficticia.gif
Pie de foto: Mesa ficticia con libros preparados para la actividad UAT.
Texto alternativo: Libros de prueba ordenados sobre una mesa vacía.
Crédito de imagen: Archivo ficticio UAT

Slug de la URL: uat-directa-rincon-lectura
Título SEO: Biblioteca escolar ficticia abre un rincón de lectura
Descripción meta: Conoce la apertura ficticia de un rincón de lectura escolar preparada para validar el CMS.
Frase clave objetivo: rincón de lectura escolar
Título para redes sociales: Nuevo rincón de lectura escolar ficticio
Descripción para redes sociales: Una actividad completamente ficticia para validar publicación y metadata social.
Imagen para redes sociales: uat-social-ficticia.gif
Pie de foto social: Tarjeta visual ficticia del rincón de lectura UAT.
Texto alternativo social: Ilustración de prueba con libros y una mesa vacía.
Crédito de imagen social: Archivo social ficticio UAT
URL canonical: dejar vacío
Excluir de los resultados de búsqueda: desmarcado
```

Noticia para workflow y privacidad:

```text
Título: UAT workflow: taller escolar prepara un boletín ficticio
Fecha de publicación: 15/07/2026
Resumen: Un taller escolar ficticio ensayó la preparación de un boletín para validar el flujo editorial.
Contenido: El Taller de Periodismo Horizonte realizó una práctica simulada. Todo el contenido, las personas y los resultados de esta noticia son ficticios.
Firma pública: Redacción del Taller Horizonte
Colaborador interno: Ana Ficticia UAT
Sección: Política
Colegio: Colegio Horizonte Ficticio
Provincia de cobertura: Arequipa
Distrito de cobertura: Cercado
Etiquetas: dejar vacío
Contiene menores identificables: marcado
Confirmo que se verificaron las autorizaciones requeridas...: marcado
Contenido sensible: desmarcado

Imagen destacada: uat-portada-ficticia.gif
Pie de foto: Materiales ficticios usados durante el taller escolar UAT.
Texto alternativo: Cuadernos y grabadoras de prueba sobre una mesa sin personas.
Crédito de imagen: Archivo del taller ficticio UAT

Slug de la URL: uat-workflow-boletin-ficticio
Título SEO: Taller escolar ficticio prepara un boletín
Descripción meta: Revisa una práctica ficticia de boletín escolar usada para validar el workflow editorial.
Frase clave objetivo: boletín escolar ficticio
Título para redes sociales: Así se preparó el boletín escolar ficticio
Descripción para redes sociales: Práctica simulada para comprobar revisión SEO, privacidad y publicación final.
Imagen para redes sociales: dejar vacío para usar la imagen destacada
Pie/alt/crédito de imagen social: dejar vacíos porque no se eligió imagen social propia
URL canonical: dejar vacío
Excluir de los resultados de búsqueda: desmarcado
```

### 1. Migración y bootstrap

1. Ejecuta `make migrate`.
2. Si la migración se detiene porque `Moderadores` o `Editores` tiene usuarios,
   no borres nada a ciegas: reasigna esas cuentas y vuelve a ejecutar. Si
   informa otra dependencia, registra el detalle y detén la UAT.
3. Ejecuta dos veces:

   ```bash
   docker compose exec web python manage.py bootstrap_mvp_access
   ```

4. Como superusuario, abre `Configuración` -> `Grupos`. El resultado esperado
   es exactamente un `Director/editor` y un `Curador SEO`; no deben existir
   `Moderadores` ni `Editores`.
5. Abre `Configuración` -> `Tareas`. Deben existir `Revisión SEO` y `Revisión
   editorial final`; no debe existir `Aprobación de moderadores`.
6. Abre `Configuración` -> `Flujos de trabajo` -> `Revisión editorial`. Verifica
   primero `Revisión SEO`, después `Revisión editorial final`, y la asignación
   del subárbol `Inicio`. No debe existir `Revisión editorial MVP` ni
   `Aprobación de moderadores`.

Resultado esperado: la segunda ejecución no duplica objetos y el estado
operativo conserva sólo los dos grupos MVP. La migración preserva cualquier
grupo, tarea o workflow no relacionado.

### 2. Cuentas y registros internos ficticios

1. En `Configuración` -> `Usuarios` -> `Añadir un usuario`, crea las dos cuentas
   de la tabla. Introduce contraseñas temporales privadas distintas en
   `Contraseña` y `Confirmación de contraseña`.
2. Reabre cada cuenta y confirma `Activo` marcado, `Administrador` desmarcado y
   exactamente el grupo indicado.
3. En `Editorial` -> `Colegios` -> `Añadir`, crea el colegio del bloque.
4. En `Editorial` -> `Grupos de colaboradores` -> `Añadir`, crea el grupo.
5. En `Editorial` -> `Colaboradores menores` -> `Añadir`, crea el colaborador.
6. En `Imágenes` -> `Añadir una imagen`, carga los dos archivos ficticios.

Resultado esperado: `uat_director` puede ver los cuatro destinos de
`Editorial`; `uat_seo` no puede ver `Editorial`, `Usuarios` ni `Grupos`.

### 3. Publicación directa como excepción autorizada

1. Entra como `uat_director`.
2. Ve a `Páginas` -> `Inicio` -> `Añadir página hija` -> `Noticia`.
3. Copia todos los valores de “Noticia de publicación directa” en las pestañas
   `Contenido` y `Asistente SEO`.
4. Selecciona `Guardar borrador`. Verifica que la noticia no aparezca en la Home
   pública anónima.
5. Reabre el borrador y selecciona `Publicar`.
6. Abre la Home pública y el detalle
   `/uat-directa-rincon-lectura/`. Verifica título, resumen, cuerpo, imagen, pie,
   crédito y firma pública.

Resultado esperado: `Publicar` funciona como override directo autorizado para
Director/editor, sin iniciar el workflow. Registra por separado que las
validaciones bloquean publicar si se elimina la firma, el pie o el alt.

### 4. Envío de la noticia al workflow

1. Como `uat_director`, crea otra `Noticia` y copia íntegramente “Noticia para
   workflow y privacidad”.
2. Usa `Guardar borrador` y confirma que sigue fuera del sitio público.
3. Selecciona exactamente `Enviar a Revisión editorial`.
4. En el dashboard confirma el encabezado `Tus páginas y elementos editoriales
   en flujo de trabajo` y que la tarea actual es `Revisión SEO`.

Resultado esperado: el workflow está activo y la noticia aún no es pública.

### 5. Aislamiento SEO, contexto de solo lectura y solicitud de cambios

1. Entra como `uat_seo`. En el dashboard confirma `Pendientes de tu revisión` y
   abre la noticia de workflow.
2. Confirma que la única pestaña visible es `Asistente SEO`.
3. En `Contexto de la noticia — solo lectura`, verifica título, `Política`,
   fecha, resumen, cuerpo completo, imagen destacada, pie, texto alternativo,
   crédito y `Redacción del Taller Horizonte`.
4. Selecciona `Previsualizar borrador completo` y verifica la revisión en una
   pestaña nueva.
5. Confirma que el contexto no contiene `Ana Ficticia UAT`, `Menor de 14 años`,
   los controles de privacidad ni la confirmación de autorizaciones.
6. Confirma que el contexto no tiene controles editables. Los únicos campos
   editables deben ser `Slug de la URL`, `Título SEO`, `Descripción meta`,
   `Frase clave objetivo`, configuración social, `URL canonical` y `Excluir de
   los resultados de búsqueda`.
7. Cambia `Descripción meta` a:

   ```text
   Revisión SEO ficticia que solicita un ajuste antes de continuar el workflow editorial.
   ```

8. Selecciona `Solicitar cambios` y escribe:

   ```text
   UAT: precisar el segundo párrafo antes de la aprobación SEO.
   ```

9. Confirma que la acción termina en el dashboard autorizado, muestra éxito y
   no presenta una pantalla de permisos.

Resultado esperado: el workflow queda `Necesita cambios`; `uat_seo` pierde el
acceso temporal de edición y ningún campo de contenido o privacidad cambia.

### 6. Reenvío y aprobación SEO

1. Como `uat_director`, reabre la noticia, añade al final del cuerpo:

   ```text
   El segundo párrafo ficticio fue precisado durante la UAT.
   ```

2. Guarda y usa `Reenviar a Revisión SEO`.
3. Como `uat_seo`, abre de nuevo `Revisión SEO` y selecciona `Aprobar` o
   `Aprobar con comentario`.
4. Confirma que vuelve al dashboard sin error de permisos.
5. Confirma que la tarea pasa a `Revisión editorial final` y que `uat_seo` ya no
   puede abrir la edición ni aprobar la tarea final.

Resultado esperado: la aprobación SEO persiste y no publica la noticia.

### 7. Revisión final y publicación normal

Como `uat_director`, abre `Revisión editorial final`. Registra las acciones
exactas que presenta esta etapa:

- `Publicar`: override directo del rol, no es la aprobación normal final.
- `Cancelar flujo de trabajo`: cancela el recorrido activo.
- `Solicitar cambios`: devuelve la revisión para corrección.
- `Aprobar y Publicar`: aprobación final normal; elige ésta para la UAT.
- `Aprobar con comentario y Publicar`: aprobación final normal con comentario.
- `Guardar borrador`: conserva cambios sin terminar el workflow.

Después de seleccionar `Aprobar y Publicar`, verifica que el workflow termina,
la noticia queda pública y aparece en la Home. Abre
`/uat-workflow-boletin-ficticio/` y confirma que incluye el segundo párrafo.

Resultado esperado: la ruta normal final es `Aprobar y Publicar`, no el override
`Publicar`.

### 8. Verificación pública de privacidad

1. En una sesión anónima, busca en la Home y en el HTML del detalle estos
   valores: `Ana Ficticia UAT`, `Menor de 14 años`, `Taller de Periodismo
   Horizonte` y `Colegio Horizonte Ficticio`.
2. `Ana Ficticia UAT` y `Menor de 14 años` no deben aparecer. El grupo interno
   tampoco debe aparecer por derivación automática. El colegio sólo puede
   aparecer si la plantilla pública lo presenta como dato editorial explícito,
   nunca como vínculo al colaborador.
3. Debe aparecer la firma pública `Redacción del Taller Horizonte`.
4. Verifica que `uat_seo` no puede abrir `Editorial` -> `Colaboradores menores`.

Resultado esperado: no hay exposición pública ni SEO del nombre interno, franja
de edad o relación interna del menor.

### 9. Contexto SEO de página institucional

1. Como `uat_director`, crea una `Página institucional` ficticia debajo de
   `Inicio`, guárdala y envíala con `Enviar a Revisión editorial`.
2. Como `uat_seo`, abre `Revisión SEO`.
3. Confirma `Contexto de la página — solo lectura`, el título y
   `Previsualizar borrador completo`.
4. Confirma que sólo son editables `Slug de la URL`, `Título SEO` y
   `Descripción meta`; no deben aparecer `Introducción`, `Contenido`, menús ni
   `Propiedades`.

Resultado esperado: Home y páginas institucionales ofrecen contexto explícito
sin ampliar los permisos SEO.

### 10. Contexto SEO de Inicio

1. Como `uat_director`, abre `Páginas` -> `Inicio` -> `Editar`.
2. No modifiques ningún campo. Selecciona `Enviar a Revisión editorial`.
3. Como `uat_seo`, abre la tarea `Revisión SEO`.
4. Confirma que la única pestaña visible es `Asistente SEO`.
5. Confirma que aparece `Contexto de la página — solo lectura`, el título de
   Inicio y la acción `Previsualizar borrador completo`.
6. Confirma que sólo son editables `Slug de la URL`, `Título SEO` y
   `Descripción meta`; no deben aparecer campos editoriales, navegación,
   menús ni `Propiedades`.
7. Selecciona `Solicitar cambios` y usa un comentario ficticio.
8. Confirma que vuelve al dashboard autorizado sin error de permisos y que la
   Home pública permanece disponible y sin cambios.
9. Como `uat_director`, abre nuevamente `Inicio` y selecciona `Cancelar flujo
   de trabajo` para no dejar la Home en moderación.

Resultado esperado: el Curador SEO dispone de contexto explícito de Inicio sin
obtener acceso de edición al contenido ni alterar la Home pública.

### 11. Ciclo de vida de cuentas y rol combinado opcional

1. Con una cuenta UAT, abre `Cuenta` -> `Cambiar contraseña` y verifica la ruta
   con una credencial temporal coordinada.
2. Como superusuario, retira un grupo, guarda y verifica la pérdida del rol;
   restáuralo sólo si queda UAT pendiente.
3. Desmarca `Activo`, guarda y confirma que no puede iniciar sesión.
4. Opcionalmente crea `uat_combined`, `Administrador` desmarcado y ambos grupos.
   Confirma que acumula las dos superficies y puede completar ambas tareas. No
   uses esta cuenta como evidencia de aislamiento.

### Limpieza

1. Despublica o elimina las páginas `uat-directa-rincon-lectura`,
   `uat-workflow-boletin-ficticio` y la institucional UAT según la política del
   entorno. Cancela primero cualquier workflow UAT que siga activo.
2. Elimina los activos `Portada ficticia UAT` e `Imagen social ficticia UAT`
   sólo cuando ninguna página los use.
3. Elimina `Ana Ficticia UAT`, `Taller de Periodismo Horizonte` y `Colegio
   Horizonte Ficticio` sólo después de retirar sus relaciones. Si el entorno
   conserva evidencia UAT, déjalos claramente identificados como ficticios.
4. Desactiva `uat_director`, `uat_seo` y `uat_combined`; elimínalos sólo si la
   política local no requiere conservar atribución de workflow.
5. No elimines `Director/editor`, `Curador SEO`, `Revisión SEO`, `Revisión
   editorial final` ni `Revisión editorial`: son configuración operativa.
