# Auditoría integral de la web — 3 de octubre de 2026

## Dictamen

La percepción de inconsistencia tiene fundamento. Hay fallos funcionales reproducibles, geometrías distintas para elementos equivalentes y controles de calidad que no comprueban lo que sus nombres sugieren. La base FastAPI + servicios + persistencia + HTML/htmx es adecuada para esta aplicación; los hallazgos no justifican sustituirla por otra arquitectura ni rediseñar arbitrariamente todas las pantallas.

El problema principal es la aplicación incompleta del sistema de diseño: compartir colores y una marca no garantiza compartir dimensiones, estados, comportamiento, composición ni reglas de adaptación. Varias decisiones locales se acumularon sin una validación transversal suficiente.

Esta entrega es un diagnóstico: no modifica la aplicación, sus datos originales ni sus contratos. Las correcciones deben comenzar por actualizar la spec correspondiente y conservar las decisiones explícitas del dueño.

## Alcance y evidencia

- Código auditado: `e847f1c`, rama base `dev`; auditoría aislada en `codex/auditoria-ui`.
- Superficies: Dashboard, Diario/Entrenamiento, Diario/Alimentación, Splits y Rumbo.
- Navegador Chromium: 1440×900, 1280×800 y 390×800. Quince capturas y mediciones sobre una copia SQLite consistente de la base real.
- Pruebas adicionales: navegación con cambios pendientes en Rumbo, envío sin JavaScript, controles móviles, respuestas 500 simuladas y contraste calculado localmente.
- Discovery con grafo del proyecto, contrastado con archivos actuales: el índice conserva información histórica y no se trató como prueba única de implementación vigente.
- Evidencia reproducible en `.tmp/evidence/`: `sweep.json`, `probe.json`, `errors.json`, `contrast.json`, capturas y salidas de pruebas. Los datos y capturas son locales.
- No se verificaron Safari, Firefox, un teléfono físico, VoiceOver, WCAG completa ni métricas de rendimiento LCP/INP/CLS. La captura tras carga no demuestra estabilidad de cada cuadro del primer pintado.

Prioridades: P1 = obstáculo funcional o posible pérdida de cambios; P2 = consistencia, claridad, accesibilidad o deuda que debe corregirse de forma planificada. No se encontró evidencia de corrupción de datos para elevar un hallazgo a P0.

## Hallazgos funcionales

### H01 — P1 — El selector de ejercicio colapsa en móvil

**Reproducción:** abrir `/diario` a 390×800, fecha vacía, vista Entrenamiento.

La celda de ejercicio mide **0 px de ancho** y el selector **16×20 px**. La captura muestra Peso/Reps/RIR/Desc, pero el campo principal de ejercicio deja de ser legible. No es solo una preferencia visual: impide reconocer y manejar adecuadamente el dato central de la serie.

**Causa:** tabla al 100% con `table-layout: fixed`; columnas numéricas de ancho fijo y columna de ejercicio sin mínimo. La suma de los anchos fijos supera el espacio disponible y consume el espacio del ejercicio. Tener un wrapper `overflow-x-auto` no basta si la tabla se comprime en lugar de tener un ancho mínimo.

**Fuentes:** `templates/session_editor.html:50–72`, `static/css/session-editor.css:142–147`; evidencia `probe.json`, `diario-390.png`.

**Corrección:** definir un mínimo útil de la tabla y la columna de ejercicio, contener el desplazamiento horizontal y comprobar que el primer campo permanece reconocible. Probar fuerza, HIIT y sesión mixta a 320/390 px, con nombres largos.

### H02 — P1 — Rumbo falla sin feedback visible ante un 500

Se interceptaron localmente `/rumbo/dia` y `/rumbo/yo` con una respuesta 500. Ambos botones vuelven a su estado normal y **`#notice-container` queda vacío**. El usuario no recibe indicación de que no se guardó.

La política de error de `htmx-lifecycle.js` solo contempla `#session-form` y `#nutrition-form`. `rumbo.js` procesa éxito de respuestas, pero no ofrece recuperación para estos fallos.

**Fuentes:** `static/js/htmx-lifecycle.js:134–169`, `static/js/rumbo.js`; `errors.json`.

**Corrección:** contrato común de mutación con estado en curso, éxito, error HTTP y error de red; conservar los valores y permitir reintento. No limitarlo al Diario. Revisar las demás mutaciones con el mismo criterio; no se afirma que todas fallen.

### H03 — P1 — Rumbo permite abandonar cambios sin advertencia

Cambiar el primer slider de 5 a 6 y pulsar Dashboard navega a `/` sin diálogo. La protección de salida únicamente consulta los formularios de entrenamiento y nutrición.

**Fuentes:** `static/js/htmx-lifecycle.js:323–330`, `static/js/rumbo.js`; `probe.json`.

**Corrección:** registrar el estado pendiente de los formularios de Rumbo —día, nombres y respuestas— y proteger la salida hasta guardar o descartar. Comprobar también el cierre de su diálogo. Extender el patrón compartido, evitando otra implementación independiente.

### H04 — P2 — Rumbo promete guardado sin JavaScript, pero no guarda

`<noscript>` afirma: «Rumbo funciona sin JavaScript: los formularios guardan igual». Los formularios solo tienen `hx-post`, sin `method` ni `action` HTML.

Con JavaScript desactivado, Guardar día navega por **GET** a `/rumbo?fecha=2026-10-03&t1=5&t2=5&t3=5`; el total sigue en 0/30. No llega al endpoint POST de guardado.

**Fuentes:** `templates/rumbo.html`, `templates/partials/rumbo_hoy.html:4`, `rumbo_yo.html:5`, `rumbo_pregunta_dialog.html:13`; `probe.json`.

**Corrección:** decidir el contrato real. Si se exige mejora progresiva, implementar POST nativo con CSRF seguro y respuesta de página completa/redirect; no basta añadir `action` porque las rutas actuales devuelven fragmentos. Si JavaScript es requisito, informar honestamente.

### H05 — P2 — El total inicial de Rumbo contradice los controles

Sin día registrado, el encabezado indica **0/30** y los controles muestran **5, 5, 5**. Tras mover uno a 6, el encabezado cambia a 16/30, aunque sigue sin guardarse.

Se mezclan en la misma etiqueta el dato persistido y la suma del borrador sin distinguirlos. El usuario no sabe si mira una puntuación guardada o una previsión.

**Fuentes:** `templates/partials/rumbo_hoy.html:3–8`, `static/js/rumbo.js:11–22`; `probe.json`.

**Corrección:** mostrar claramente «sin registro» y distinguir borrador/guardado; acordar qué valores iniciales corresponden al dominio. No introducir 0 en sliders cuyo contrato actual es 1–10 sin ajustar la spec.

## Hallazgos de diseño y adaptación

### H06 — P2 — Alturas rígidas producen espacios muertos y alejan Guardar

El editor de entrenamiento reserva **452 px** para su tabla y nutrición **516 px**, independientemente del número de filas. Una sesión con una sola fila deja gran parte de la tarjeta vacía. A 390×800, Guardar cambios queda alrededor de y=919, por debajo del primer viewport. En escritorio también queda bajo el límite visible de la columna y requiere scroll interno.

Es un costo real de usabilidad, aunque la reserva histórica busca evitar saltos visuales. No debe eliminarse sin revisar ese contrato.

**Fuente:** `static/css/session-editor.css:110–131`; `diario-1440.png`, `diario-390.png`, `sweep.json`.

**Corrección:** altura acotada y adaptable por estado/contenido; probar estabilidad al cargar, editar, añadir filas y guardar. Mantener las acciones de guardado accesibles sin atravesar una zona vacía.

### H07 — P2 — Diario deja una franja derecha que no existe en otras pestañas

A 1440 px, su columna principal comienza en x=299 y queda limitada a **960 px**: termina en x=1259, dejando **157 px** hasta el borde de contenido x=1416. Rumbo y Splits ocupan 1117 px en ese mismo espacio.

La restricción es explícita: `#daily-page .splits-editor-col { max-width: 960px; }`. No es un fallo aleatorio del navegador.

**Fuente:** `static/css/diario.css:44–45`; `sweep.json`.

**Corrección:** definir una política común de anchura. Si el formulario debe conservar un ancho máximo por legibilidad, justificar y resolver su alineación como variante formal; evitar dejarlo como excepción suelta.

### H08 — P2 — La cabecera cambia de posición y altura

Mediciones a 1440×900:

| Superficie | Inicio de nav X | Inicio contenido Y |
|---|---:|---:|
| Dashboard | 645 | 83 |
| Diario | 651 | 85 |
| Splits | 577 | 93 |
| Rumbo | 651 | 85 |

El botón Nuevo split ocupa espacio en la misma fila que una marca centrada con flex, por lo que el grupo se centra dentro del espacio restante y se desplaza. Dashboard además tiene `padding-bottom:14px`, frente a 16px del header compartido.

En móvil el inicio de contenido es y=163/121/169/121 respectivamente; parte de la diferencia viene de controles legítimos, pero el shell no distingue cabecera estable y toolbar variable.

**Fuentes:** `static/css/components.css:135–146,576–587`, `static/css/cascade.css:64–77`, `templates/splits.html`; `sweep.json`.

**Corrección:** estructura compartida para marca/nav con alineación independiente de acciones, y toolbar explícita. No exigir idéntico contenido; sí idéntico comportamiento de los elementos equivalentes.

### H09 — P2 — Rumbo representa ausencia de datos como un gráfico grande vacío

La tendencia anual muestra un SVG sin barras visibles, un eje y «pico 0/210». El SVG mantiene la proporción 520:120; a 1117px de ancho ocupa unos 250px de alto, agrandando la zona vacía. La tarjeta anual mide unos **340px** y desplaza los controles de nombres bajo el scroll de la columna.

**Fuentes:** `templates/partials/rumbo_anual.html`, `.rumbo-trend` en `static/css/rumbo.css`; `rumbo-1440.png`.

**Corrección:** estado vacío explícito, con altura útil y explicación de cómo comenzar; conservar el gráfico para datos reales. Ausencia de observaciones y cero observado deben distinguirse.

### H10 — P2 — Contraste insuficiente comprobado en Rumbo

La ayuda «52 semanas · pico» usa `rgb(115,115,115)` sobre `rgb(23,23,23)`, tamaño 12px: contraste **3.78:1**, inferior al 4.5:1 requerido para texto normal por WCAG 1.4.3. Se calculó localmente a partir de los estilos efectivos, sin auditor externo.

**Fuente:** `static/css/rumbo.css:21–24`; `contrast.json`.

**Corrección:** usar un token de texto secundario que cumpla el contraste, y revisar otras ayudas activas; no contar campos deshabilitados como incumplimiento automático.

Referencia: [W3C — contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

### H11 — P2 — Tamaño táctil y descubrimiento de acciones no tienen un contrato efectivo común

Los inputs de las tablas miden 20px de alto y el lápiz 24px; el estándar interno solicita objetivos de 44×44px en botones/inputs del editor. Las acciones de fila son visualmente 14×14px, pero tienen un pseudo-elemento expansor a 24px: **no deben declararse incumplimiento WCAG solo por su bounding box**. Falta verificar colisiones entre áreas expandidas y su uso táctil. Algunas acciones además se revelan por hover/foco/active, lo que reduce su descubrimiento en móvil.

**Fuentes:** `docs/architecture/web-standards.md`, `static/css/session-editor.css:34–43,230–278`; `sweep.json`.

**Corrección:** distinguir densidad visual y área real de interacción, verificar interacción táctil y separación. WCAG 2.2 AA exige 24px o una excepción válida de espaciado; 44px es un objetivo interno más exigente, no el mínimo AA.

Referencia: [W3C — tamaño mínimo](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

## Arquitectura, contratos y controles de calidad

### H12 — P2 — Las specs y la implementación ya divergen

Spec 043 exige shell fijo de Rumbo (`100vh`, flex columna, `overflow:hidden` de escritorio). El CSS actual conserva el patrón de spec 040 con padding y columnas `max-height:calc(100dvh - 164px)`; no restaura esas reglas específicas. El test de encaje puede pasar porque el body ya tiene min-height de viewport y las columnas están acotadas: eso no demuestra restauración literal del shell.

La constitución también cita límite de 500 líneas, mientras AGENTS/gate admiten 800 con aviso a 500; el contrato histórico aún describe undo global por atajo, pero el listener actual aplica undo local de campos. No presentar documentación histórica como verdad vigente sin reconciliarla.

**Fuentes:** `specs/040-shell-canonico/spec.md`, `specs/043-revert-rumbo/spec.md`, `docs/constitution.md`, `docs/architecture/current-ui-contract.md`, `scripts/check_file_size.py`, `static/js/htmx-lifecycle.js:302–317`.

**Corrección:** una referencia vigente explícita por contrato y decisiones/supersesiones claras. Resolver cuál debe ser el comportamiento antes de «armonizar» contra una decisión previa.

### H13 — P2 — Los gates producen confianza incompleta

- `audit_consistency.py` pasa. Comprueba patrones de clases/colores/includes, **no** geometría, equivalencia de estados o adaptación móvil. Sus funciones de coverage de componentes no prueban todas las clases utilizadas ni sus medidas.
- `audit_ui.py` busca el popup retirado, `#cascade-row` y el botón `open-editor-popup`; no es un barrido vigente de las cuatro pestañas. Ejecutarlo sin actualizar puede fallar por supuestos viejos.
- `test_encaje_exacto.py` comprueba la altura del documento, pero no las bases de cada región. `body.min-h-screen` puede satisfacer su mínimo sin que el contenido rellene la pantalla.
- Los tests axe existentes usan tags hasta WCAG 2.1, sin `wcag22aa`, y no recorren Rumbo/Splits ni la pestaña Alimentación activa en el caso básico.
- Los fixtures de navegador tienen pocos datos: no reflejan la densidad de una base histórica real.

**Corrección:** separar checks de vocabulario, geometría, interacción, accesibilidad y datos densos; sumar aserciones sobre anchos mínimos útiles, posición de Guardar, origen de cabecera, pendientes y estados de error. Una captura complementa una prueba, no la sustituye.

### H14 — P2 — La atomicidad se exige al backend pero no al frontend

Archivos actuales: `components.css` 1392 líneas, `splits.js` 1211, `chart-interaction.js` 860 (líneas físicas). El gate solo incluye app/src/scripts/tests y cuenta principalmente Python; no controla estos módulos. No se equiparan líneas físicas a líneas de código del gate, pero su cobertura deja fuera precisamente la capa donde aparecen las divergencias.

El bootstrap comparte inicializadores de editor en Dashboard y Diario, mientras Rumbo implementa su propio ciclo y carece de protecciones comunes. Los handlers repartidos por documento y las reglas por id hacen fácil que un cambio mejore una página sin alcanzar las demás.

**Corrección:** extraer responsabilidades coherentes —shell, ciclo de mutación, tablas/editor, estados pendientes— con contratos pequeños. Dividir por responsabilidad, no por cuotas arbitrarias de líneas. Mantener la delegación de eventos y HTML/htmx; no introducir una SPA para resolver esto.

## Lo que funciona y debe preservarse

Las quince cargas de página tuvieron estado `appReady=1`, HTTP 200, cero excepciones JavaScript capturadas, cero IDs duplicados y cero desbordamiento horizontal global. Los campos visibles revisados tenían label o nombre accesible; esto no equivale a una auditoría completa de nombres/calidad semántica.

El shell base, navegación con `aria-current`, controles nativos, datos server-side, configuración JSON inerte, tokens de color, módulos JS y fronteras de servicio/persistencia son bases razonables. El uso de tres columnas en análisis y dos en edición es una diferencia funcional válida. El scroll horizontal confinado de un board semanal tampoco es por sí mismo un fallo.

La excepción histórica de reordenamiento solo con ratón y el retiro deliberado de undo visible deben respetarse como decisiones del producto; no «corregirlos» silenciosamente. No se certifica WCAG AA global con una excepción de teclado conocida.

## Orden de corrección propuesto

1. Resolver H01, H02 y H03: selección móvil, errores silenciosos y cambios pendientes.
2. Aclarar el estado de Rumbo y su requisito de JavaScript (H04–H05).
3. Acordar el contrato visual transversal: anchos, cabecera, altura por estado, acciones de guardado y vacíos (H06–H09), conservando excepciones justificadas.
4. Corregir contraste y verificar áreas reales de interacción (H10–H11).
5. Reconciliar documentos/specs y actualizar gates antes de ampliar el rediseño (H12–H14).

Criterio de aceptación transversal: mismas reglas para elementos equivalentes, diferencias explicadas por la tarea, contenido legible y operable a 320/390px, acciones accesibles con poca o mucha información, estados claros de borrador/guardado/error y pruebas de recarga/persistencia para cada mutación. Aprobar una imagen aislada no basta.

## Validación

- Consistencia UI: pasa; tamaño: pasa con avisos; Ruff lint y formato: pasan (318 archivos formateados); mypy: sin errores en 151 archivos. Cobertura por módulo: charts 93%, metrics_engine 97%.
- Unidad/integración: 944 pasan y 3 fallan por acceso de red del sandbox; cobertura de la ejecución 91.44%. Los mismos 3 tests se repitieron con acceso de red y pasaron. No se presenta como una única ejecución completa en verde.
- E2E: 213 passed, 1 skipped in 635.50s (0:10:35). Pruebas con datos sintéticos aislados; no sustituyen las comprobaciones con datos reales copiados de esta auditoría.
- Auditor externo axe sobre la copia personal: rechazado por revisión automática de aprobación debido a acceso potencial del código de terceros al DOM. No se ejecutó ese script. Se continuó con mediciones propias locales; su cobertura completa queda pendiente.

## Evaluación crítica del diagnóstico

**Dictamen:** aplicación funcional con una base técnica razonable, pero con calidad de interfaz insuficiente para considerarla consolidada. La evidencia justifica una remediación por contratos compartidos; no justifica una reescritura ni certifica profesionalmente toda la arquitectura.

La solidez de los hallazgos no es uniforme:

- H01–H05: defectos o contradicciones reproducidos. H01–H03 tienen prioridad por impacto en uso y conservación de cambios; H04 requiere decidir si el producto necesita realmente funcionar sin JavaScript.
- H10: contraste puntual medido; no equivale a una auditoría completa de accesibilidad.
- H06–H09: costos de diseño demostrados mediante geometría y capturas. El espacio vacío, un ancho máximo o una cabecera más alta no son defectos por sí mismos. Deben juzgarse por legibilidad, acceso a acciones y estabilidad; varias reglas provienen de decisiones anteriores que necesitan revisarse conscientemente.
- H11: incumplimiento de la meta interna de tamaño y riesgo táctil; falta comprobar hit areas, separación y excepciones antes de afirmar incumplimiento WCAG general.
- H12–H13: desajustes concretos entre contrato, implementación y pruebas. Conviene reconciliarlos al iniciar cada corrección, no dejarlos para después de implementarla.
- H14: evidencia de deuda de mantenimiento y alcance incompleto del gate. La longitud de un archivo no prueba por sí sola mala arquitectura ni demuestra que causó los defectos observados.

**Límite de la conclusión arquitectónica:** se revisaron el ensamblaje de las pantallas, sus estilos, inicialización, formularios y contratos relevantes. No se realizó una verificación exhaustiva de dependencias, transacciones, seguridad o invariantes de todos los servicios. No hay evidencia suficiente para declarar violaciones generalizadas de SOLID ni para certificar íntegramente la arquitectura del backend.

**Secuencia ajustada:** para cada lote, primero reconciliar su contrato y escribir una prueba que reproduzca el problema; después corregir y validar. Empezar por selección móvil, errores y cambios pendientes. Continuar con estado de Rumbo y contraste. Unificar después cabecera, anchos y alturas con decisiones visuales explícitas. Modularizar solo donde facilite esos contratos o reduzca un acoplamiento demostrado.

**Aceptación:** un fallo 500 debe producir un aviso útil; salir con un borrador debe permitir guardar o descartar; el selector de ejercicio debe ser legible y operable en móvil; el estado visible debe distinguir borrador y registro; la cabecera común debe conservar su alineación al añadir acciones; los estados vacíos deben explicar su situación y mantener accesibles las acciones. Las pruebas existentes en verde son una base, pero estas condiciones deben incorporarse antes de declarar corregida la experiencia.
