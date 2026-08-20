# Guía de defensa — SIG-LOG

Respuestas a las preguntas que se hacen en la revisión, cada una con el
archivo y la línea donde está el código que la contesta. No memorices
números: memoriza **dónde** se calculan.

---

## 1. ¿Cómo obtiene los datos?

Tres esquemas en una sola base de datos PostgreSQL:

| Esquema | Qué guarda | Quién escribe |
|---|---|---|
| `public` | Operación diaria: clientes, vehículos, operadores, rutas, entregas, combustible, mantenimiento | Los siete módulos de captura |
| `staging` | Copia cruda de lo extraído, antes de limpiar | El ETL, fase Extract |
| `dw` | Modelo estrella: 7 dimensiones + 3 tablas de hechos | El ETL, fase Load |

El flujo es: **capturas** en `public` → **`python manage.py run_etl`** mueve,
limpia y carga → las pantallas de análisis leen **solo `dw`**.

La frase corta para decir en voz alta: *"Los reportes no consultan las tablas
de captura. Consultan un almacén dimensional que un proceso ETL puebla, y por
eso una consulta que cruza seis entidades no necesita seis JOINs."*

**Código:** `warehouse/etl/extract.py`, `transform.py`, `load.py`;
orquestados por `warehouse/management/commands/run_etl.py`.

**La única excepción, y hay que saberla:** las alertas de mantenimiento
(`/reportes/mantenimiento/`) leen `public`, no `dw`, a propósito. "¿Qué
vehículo necesita servicio hoy?" es una pregunta operativa que debe responder
con el odómetro de este momento, no con el del último ETL. Está documentado
como decisión en `docs/Arquitectura.md`, sección 6, y hay una prueba que lo
fija: `test_alerts_come_from_the_oltp_not_the_warehouse`.

---

## 2. ¿Cómo sabe de qué periodo son los datos?

La dimensión `dw.dim_date` tiene una fila por día con `full_date` (indexada),
`year`, `quarter`, `month`, `week`, `fortnight` y `day_of_week`. Las tres
tablas de hechos apuntan a ella con una llave foránea.

El filtro es la clase `Period` en `apps/analytics/queries.py:22`. Guarda un
rango con ambos extremos opcionales, y `_scope()` (línea 52) lo aplica:

```python
queryset.filter(date__full_date__gte=period.start)
queryset.filter(date__full_date__lte=period.end)
```

Las nueve funciones de consulta reciben `period=None`. El filtro está escrito
**una vez**, no nueve: por eso `_deliveries()`, `_fuel()` y `_maintenance()`
existen.

En pantalla: el selector arriba de las seis pantallas de reportes, con campos
Desde/Hasta y cuatro atajos. El rango vigente se anuncia a la derecha
("Periodo: 1 de marzo de 2026 — 31 de marzo de 2026").

**Detalle que conviene que tú menciones antes de que él lo note:** los atajos
("Último mes", "Último trimestre") se cuentan desde **la última fecha con
datos**, no desde hoy. El almacén termina el 2026-07-31; contarlos desde la
fecha actual devolvería pantallas vacías. Está en
`apps/analytics/queries.py:79` (`data_bounds`) y en
`apps/analytics/forms.py` (`PeriodForm.period`).

**Si te pide un periodo específico:** escríbelo en Desde/Hasta y aplica. Las
exportaciones arrastran el mismo rango, porque los enlaces llevan la cadena
de consulta.

---

## 3. ¿Cómo calcula los porcentajes?

Todos en `apps/analytics/queries.py`. Son cuatro fórmulas distintas:

| Porcentaje | Fórmula | Dónde |
|---|---|---|
| Cumplimiento | `(total − retrasadas) / total × 100` | `kpi_summary` |
| % de retraso de una ruta u operador | `retrasadas del grupo / envíos del grupo × 100` | `top_routes`, `top_operators` |
| Participación de un servicio | `envíos del grupo / total de envíos × 100` | `demand_by_service_type` |
| Acumulado del Pareto | `suma corriente / gran total × 100` | `delay_causes_pareto` |

Los tres primeros dividen en Python sobre valores que SQL ya agregó con
`Count()`. El Pareto acumula en un `for` porque cada punto depende del
anterior.

**Protección contra división entre cero:** cuando el periodo no tiene datos,
`total` es 0 y la expresión es `... if total else 0.0`. En el Pareto es
`grand_total = sum(counts) or 1`. Hay una prueba que lo fija:
`test_an_empty_period_answers_zero_instead_of_crashing`. Si te pide un
periodo sin datos (diciembre de 2026, por ejemplo), la pantalla muestra ceros
en lugar de reventar. **Pruébalo antes de entrar.**

En las gráficas de pastel el porcentaje se escribe en la leyenda y en el
tooltip con `siglogPercentLabels` y `siglogPercentTooltip`, en
`static/js/charts.js`.

---

## 4. ¿Cómo obtiene el promedio?

Dos mecanismos, y **hay que distinguirlos porque es la pregunta trampa**:

**En los datos**, con `Avg()` de SQL, que se traduce a `AVG()` de PostgreSQL:
retraso promedio, rendimiento km/L, costo por kilómetro, duración promedio.
Ejemplo en `kpi_summary` y en `worst_routes`.

**En las gráficas**, con `siglogAverage()` de `static/js/charts.js`, dibujado
como línea punteada gris con su valor escrito en la leyenda.

> **La distinción que tienes que decir tú primero:** la línea de promedio de
> la gráfica es el promedio **de las diez barras mostradas**, no de las 60
> rutas. El promedio global vive en las tarjetas del panel. Son dos números
> distintos y ambos son correctos; lo que sería incorrecto es confundirlos.

**El segundo caso de confusión, ya resuelto en el sistema:** el retraso
promedio tiene dos lecturas legítimas.

| Conjunto | Entregas | Promedio |
|---|---:|---:|
| Todas las entregas | 26,886 | **29.2 min** |
| Solo las que excedieron la tolerancia | 12,866 | **57.4 min** |
| Solo las puntuales | 14,020 | 3.3 min |

El panel muestra **las dos** en tarjetas separadas y rotuladas, precisamente
para que no haya ambigüedad. Si pregunta "¿ese promedio es de todas o solo de
las tardías?", la respuesta es: "de las dos maneras, y están las dos en
pantalla".

La tolerancia son 15 minutos: `DELAY_TOLERANCE_MINUTES` en
`apps/deliveries/models.py:11` y en `warehouse/etl/transform.py:14`. Una
entrega cuenta como retrasada solo si excede **estrictamente** esos 15
minutos.

---

## 5. ¿Cómo determina cuál es el punto más alto?

Dos formas, según dónde se necesite:

**En SQL**, ordenando y recortando: `.order_by("-shipments")[:limit]`. El
primer renglón de la tabla **es** el máximo; no hay un cálculo aparte. Eso
genera `ORDER BY ... DESC LIMIT 10` en PostgreSQL.

**En la gráfica**, con `Math.max(...values)` en `static/js/charts.js`:

- `siglogMaxColors` pinta la barra más alta en el color de acento (naranja) y
  las demás en el color base.
- `siglogPeakSubtitle` escribe el subtítulo: *"Máximo: RUT-009 con 167
  envíos"*, con el nombre y el valor.

Así que el punto más alto está señalado de tres maneras a la vez: es el
primer renglón de la tabla, es la barra naranja, y está nombrado en el
subtítulo.

---

## 6. ¿Cómo genera los reportes?

`apps/analytics/exports.py` tiene un diccionario `REPORTS`: ocho entradas,
cada una con su etiqueta, su función constructora y sus columnas con el
encabezado en español.

```python
"rutas": {
    "label": "Rutas más utilizadas",
    "builder": lambda period=None: queries.top_routes(limit=100, period=period),
    "columns": [("code", "Código"), ("name", "Ruta"), ...],
}
```

Una sola vista los sirve todos (`export_report`), y el formato es la única
bifurcación: `to_csv` escribe con `csv.writer` y un BOM al inicio para que
Excel lea los acentos; `to_excel` arma un `DataFrame` de pandas y lo escribe
con openpyxl.

**Agregar un reporte nuevo es agregar una entrada al diccionario.** No hace
falta tocar la vista ni las URLs. Si te pide un reporte que no existe, esto
es lo que se edita, y son unas seis líneas.

Los ocho disponibles hoy: rutas más utilizadas, rutas con mayores retrasos,
operadores con más entregas, costo por vehículo, rendimiento por vehículo,
costo por kilómetro, demanda por servicio y demanda por cliente. Todos en CSV
y en Excel, todos acotados al periodo de la pantalla.

---

## 7. ¿De dónde salen los datos de las gráficas?

De la base de datos, por este camino y sin AJAX:

1. La vista llama a `queries.*` con el periodo.
2. La consulta devuelve listas y diccionarios de Python planos — nunca
   objetos del ORM, para que la plantilla no pueda disparar consultas.
3. La vista pone esos datos en el contexto con el sufijo `_json`.
4. La plantilla los serializa con el filtro `json_script` de Django, que
   escribe un `<script type="application/json">` en el HTML.
5. El JavaScript los lee del DOM con `JSON.parse` y los pasa a Chart.js.

La frase para decir: *"Si abres el código fuente de la página, los datos de
la gráfica están ahí, en JSON, generados por PostgreSQL. El JavaScript no
calcula ni inventa nada; solo dibuja."*

Las dos únicas cosas que sí calcula el JavaScript son el promedio de la serie
mostrada y cuál es el máximo — ambas sobre los datos que ya vinieron del
servidor.

---

## Cambios en vivo: dónde tocar

| Si te pide… | Edita | Qué |
|---|---|---|
| Otro color en una gráfica | `static/js/charts.js` | El valor en `SIGLOG_COLORS`. Un solo lugar para todo el sistema |
| Otro tipo de gráfica | la plantilla | `type: "pie"` → `"bar"`, `"line"`, `"doughnut"`, `"polarArea"` |
| Más o menos filas | `apps/analytics/views.py` | El `limit=10` de la consulta |
| Otro periodo | nada | Ya está en la interfaz |
| Que se vea el promedio | nada | Ya está; es la línea punteada |
| Que se vea el máximo | nada | Ya está; es la barra naranja y el subtítulo |
| Porcentajes en un pastel | nada | Ya están en la leyenda y el tooltip |

Los colores disponibles por nombre: `primary` (azul), `secondary` (verde),
`accent` (naranja), `average` (gris), `danger` (rojo), y el arreglo `pie` con
seis colores para los pasteles. Si pide "morado", el valor hexadecimal es
`#6f42c1`; "rosa" es `#d63384`; "azul cielo" es `#0dcaf0`.

**Después de editar un archivo estático, recarga con Ctrl+F5**, porque el
navegador cachea el JavaScript. Si editas una plantilla y no ves el cambio,
reinicia `runserver`.

---

## Los reportes que puede pedir, y dónde están

| Lo que pida | Dónde | Qué muestra |
|---|---|---|
| Rendimiento de empleados | `/reportes/operacion/` → tabla de operadores | Entregas y % de retraso por operador, exportable |
| "Vendedores" con más ventas | mismo | El equivalente en este dominio: operadores con más entregas. También `demanda-cliente` da los clientes por flete |
| Ventas por periodo | `/reportes/` → tendencia mensual | Entregas y flete por mes, con el filtro de periodo |
| Porcentajes | `/reportes/operacion/` | Participación por servicio, % de retraso, Pareto acumulado |
| Promedios | `/reportes/` tarjetas, y la línea en cada gráfica | Retraso, rendimiento, costo por km |
| Vehículos con más costo | `/reportes/costos/` | Combustible + mantenimiento, apilado |
| Predicción de retraso | `/reportes/prediccion/` | Formulario; F1 0.7795 |
| Grupos de rutas | `/reportes/conglomerados/` | 3 grupos, silueta 0.7381 |

Si pide "ventas", traduce en voz alta: *"en este dominio la venta es el flete
cobrado por entrega, que es el campo `freight_cost`"*. No lo dejes pasar como
si fuera lo mismo sin decirlo.

---

## Preguntas incómodas, con respuesta honesta

**"¿Por qué el cumplimiento es apenas 52%?"**
Porque la tolerancia es de 15 minutos y los datos son sintéticos, generados
con patrones deliberados: las rutas urbanas congestionadas tienen una tasa de
retraso sembrada cercana al 68%. No es un error del cálculo, es el escenario
que el generador construye para que el análisis tenga algo que encontrar.
`seed/patterns.py`.

**"¿Los datos son reales?"**
No. Son sintéticos, generados por `seed_demo` con semilla fija 42, lo que los
hace reproducibles: cualquiera que corra el comando obtiene exactamente los
mismos 26,886 registros. Está dicho en el README y en los manuales.

**"¿Por qué el R² de la regresión es 0.226?"**
Porque predecir *cuántos* minutos se retrasará una entrega, con solo las
variables conocidas antes de salir, es un problema con mucho ruido
irreducible. La clasificación (¿llegará tarde, sí o no?) sí funciona bien:
F1 0.7795. El análisis completo está en `docs/U3_Analisis_Supervisado.md`,
sección 4. No lo defiendas como si fuera bueno; explica por qué es esperable.

**"¿Por qué elegiste tres conglomerados?"**
Por el barrido de k de 2 a 10 con dos métricas: la silueta llega a su máximo
en k=3 (0.7381) y el codo de la inercia también quiebra ahí. Con k=4 la
silueta es prácticamente igual, y elegí el modelo más simple. Las gráficas
del barrido están en la pantalla de conglomerados.

**"Elegí un solo mes y la tendencia mensual quedó con un punto."**
Correcto: la tendencia agrupa por mes, así que un mes es un punto. Para ver
la tendencia hay que abrir el rango; para ver el detalle de un mes están el
mapa de calor por día y hora y las tablas.

**"¿Dónde está la validación de los datos?"**
En dos capas. Los formularios rechazan lo imposible al capturar. Y el ETL
aplica **ocho técnicas de limpieza**, que conviene nombrar así y no por el
nombre de la función:

1. Normalización (espacios, mayúsculas, placas con guiones)
2. Tratamiento de nulos (ciudad vacía → `DESCONOCIDA`)
3. Deduplicación por clave natural
4. Validación de rango (litros ≤ 0, flete negativo)
5. Coherencia temporal (llegada anterior a la salida)
6. Integridad referencial
7. Detección de atípicos (rendimiento fuera de 1.0–12.0 km/L)
8. Exclusión de entregas abiertas (sin hora de llegada)

Están en `warehouse/etl/cleaning.py` y cada una tiene prueba con caso válido
e inválido. Lo que no pasa **no se descarta en silencio**: va a cuarentena en
`dw.etl_error` con la regla que lo rechazó y su carga original. Hoy hay 352
registros ahí, y el desglose es 272 por coherencia temporal, 52 entregas
abiertas, 10 por litros ≤ 0, 10 atípicos de rendimiento y 8 por flete
negativo. La tabla se puede consultar en vivo si lo pide.

---

## Antes de entrar

```powershell
conda activate siglog
python manage.py runserver
```

Y comprueba, en este orden, que no haya sorpresas:

1. Entra con tu usuario. Si no lo recuerdas:
   `python manage.py changepassword <usuario>`.
2. Abre las seis pantallas de reportes. Las seis deben pintar.
3. Aplica "Último mes" y confirma que los números **cambian**.
4. Aplica un rango sin datos (2026-12-01 a 2026-12-31) y confirma que
   muestra ceros sin error.
5. Descarga un CSV y un Excel.
6. Manda una predicción en `/reportes/prediccion/`.

Si algo falla, `python manage.py test` en 217+ pruebas dice qué se rompió.
