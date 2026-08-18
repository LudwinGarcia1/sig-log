# Arquitectura — SIG-LOG

Este documento registra las decisiones de diseño del sistema: qué se eligió,
qué se descartó, por qué, y qué cuesta la elección. No es un recorrido por
los archivos — eso está en `docs/Manual_Tecnico.md`.

## 1. Tres esquemas, una base de datos

```
public   →  OLTP     los 8 módulos de negocio, escritura en vivo
staging  →  landing  extracción cruda del ETL, sin transformar
dw       →  estrella dimensiones, hechos y bitácoras
```

**Se eligió:** un único servidor PostgreSQL con tres esquemas, declarando el
esquema directamente en `db_table` de cada modelo del almacén
(`db_table = 'dw"."fact_delivery'`). Una migración inicial de `warehouse`
(`0001_create_schemas.py`) ejecuta `CREATE SCHEMA IF NOT EXISTS` para
`staging` y `dw` antes de cualquier otra operación, así que las tablas
siempre encuentran su esquema creado.

**Se descartó:** un router de bases de datos por alias con `search_path`
distinto por conexión, que es la alternativa "formal" en Django para separar
sistemas transaccionales de analíticos.

**Por qué:** con tres esquemas en una sola base, el ORM de Django sigue
disponible tal cual para las consultas del dashboard (`apps/analytics`
importa `warehouse.models` directamente), sin una segunda configuración de
conexión ni lógica de enrutamiento. Es la solución pragmática de uso
extendido para este alcance.

**Costo:** las tres bases lógicas comparten un mismo servidor físico —no hay
aislamiento de recursos entre OLTP y almacén— y `db_table` con comillas
incrustadas es una convención frágil si alguien la edita sin cuidado. Para
un proyecto de una sola base de datos y una sola persona operándolo, ese
costo es aceptable.

## 2. Interfaz: plantillas de Django, no una API

**Se eligió:** Django Templates + Bootstrap 5, un monolito renderizado en
servidor.

**Se descartó:** una API con Django REST Framework y un frontend en
JavaScript separado (React, Vue).

**Por qué:** un solo lenguaje y un solo proceso para capturar, calcular y
mostrar reduce las piezas móviles del proyecto, y es más rápido de
documentar con capturas de pantalla porque no hay una capa de API que
describir por separado.

**Costo:** sin una API, el sistema no es consumible por un cliente móvil ni
por otro sistema externo sin construir esa capa después. Está fuera del
alcance comprometido (`docs/superpowers/specs/2026-08-16-sig-log-design.md`,
§2.1).

## 3. Modelo estrella, no copo de nieve

**Se eligió:** siete dimensiones desnormalizadas (`dim_date`, `dim_time`,
`dim_customer`, `dim_vehicle`, `dim_operator`, `dim_route`,
`dim_delay_cause`) y tres tablas de hechos.

**Se descartó:** normalizar las dimensiones en un copo de nieve (por
ejemplo, separar ciudad y estado de `dim_customer` en su propia tabla).

**Por qué:** las consultas del dashboard (`apps/analytics/queries.py`)
necesitan un solo `JOIN` por dimensión, y el esquema es más fácil de explicar
a quien lo audite.

**Costo:** redundancia de atributos como ciudad o marca repetidos en cada
fila de la dimensión. A esta escala (decenas de miles de filas) ese costo es
irrelevante.

## 4. Tres hechos, no uno

**Se eligió:** `fact_delivery`, `fact_fuel` y `fact_maintenance` como tablas
separadas.

**Se descartó:** una sola tabla de hechos con todas las medidas.

**Por qué:** los tres granos son distintos — una entrega, una carga de
combustible y una orden de servicio no ocurren juntas ni comparten cardinalidad.
Forzarlas a una tabla común produciría filas con la mitad de las columnas
nulas, que es precisamente el error que el modelado dimensional enseña a
evitar. Detalle de las tres granularidades en `docs/U2_Data_Warehouse.md`.

**Costo:** cualquier pregunta que cruce las tres (por ejemplo, costo total
de operar un vehículo por período) exige agregarlas por separado y sumar en
la capa de aplicación (`apps/analytics/queries.py::cost_by_vehicle` hace
exactamente eso), en vez de una sola consulta con `SUM` sobre una tabla
única.

## 5. SCD tipo 1, no tipo 2

**Se eligió:** las dimensiones se actualizan por *upsert* sobre su clave
natural — el valor anterior se sobrescribe (`warehouse/etl/load.py`,
`_load_dimension`).

**Se descartó:** SCD tipo 2, que conservaría cada versión histórica de un
atributo con fechas de vigencia.

**Por qué:** SCD tipo 2 exige columnas de vigencia y versionado, y consultas
que siempre filtren por la versión vigente. Este alcance no tiene una
pregunta de negocio que dependa de saber cómo era un cliente o un vehículo
en el pasado — solo cómo son ahora.

**Costo:** si el tipo de un vehículo o la zona de una ruta cambiara,
history se pierde: los hechos ya cargados quedarían asociados a la versión
más reciente de la dimensión, no a la que tenían cuando ocurrió la entrega.
Documentado como decisión consciente, no como omisión.

## 6. Alertas de mantenimiento sobre el OLTP, no sobre el almacén

**Se eligió:** `apps/vehicles/services.py::maintenance_alerts()` consulta
directamente `Vehicle` en `public`.

**Se descartó:** calcular la misma alerta desde `dw.fact_maintenance` y
`dw.dim_vehicle`.

**Por qué:** "¿qué vehículo necesita servicio hoy?" es una pregunta
operativa que exige el estado más reciente del vehículo. El almacén se
recarga por lotes (`run_etl`), así que consultarlo para esta pregunta
podría mostrar un vehículo como disponible cuando en realidad ya cruzó su
kilometraje de servicio hace una hora.

**Costo:** esta es la única vista de `analytics` que no lee el almacén, lo
que rompe la uniformidad de que "todo reporte viene del DW" — una
inconsistencia deliberada, señalada explícitamente en el código
(`apps/analytics/views.py::alerts`, comentario de la función) y en la
plantilla misma (`templates/analytics/alerts.html`).

## 7. `db_table` con esquema, no un router de bases de datos

Ver también la decisión 1. Como alternativa de contingencia, si
`db_table = 'dw"."tabla'` diera problemas en alguna operación de migración,
la especificación de diseño deja registrada la alternativa: crear las
tablas del almacén con `RunSQL` explícito y consultarlas desde
`pandas.read_sql` en vez de a través del ORM. No fue necesaria: las
migraciones de `warehouse` corrieron sin incidentes.

## 8. Diagramas

### 8.1 Capas de un módulo de negocio

```
HTTP request
     │
     ▼
 views.py   ── protocolo HTTP, redirecciones, contexto de plantilla
     │
     ▼
 forms.py   ── validación estricta, transformación de la entrada
     │
     ▼
services.py ── lógica de negocio, cálculos, transacciones (solo donde aplica)
     │
     ▼
 models.py  ── comportamiento inherente de la entidad
     │
     ▼
 PostgreSQL (esquema public)
```

### 8.2 Esquema estrella del data warehouse

```
                dim_date        dim_time
                    \               /
                     \             /
   dim_customer ── fact_delivery ── dim_route
                     /      |      \
              dim_vehicle   |    dim_operator
                             \
                       dim_delay_cause

   dim_vehicle ── fact_fuel ── dim_operator      (+ dim_date, dim_time)

   dim_vehicle ── fact_maintenance               (+ dim_date)
```

### 8.3 Flujo del ETL

```
public.*  ──Extract──▶  staging.stg_*  ──Transform──▶  registros limpios en memoria
                                                              │
                                        fila inválida ────────┼───▶ dw.etl_error
                                                              │
                                                              ▼
                                                  Load (transacción única)
                                                              │
                                          ┌───────────────────┼───────────────────┐
                                          ▼                   ▼                   ▼
                                   dw.dim_* (upsert)   dw.fact_* (bulk_create)   dw.etl_log
```

Cada flecha de fase escribe su propia bitácora en `dw.etl_log`; el flujo
completo y la decisión sobre por qué un fallo en Load no deja rastro en el
log de esa fase están en `docs/Manual_Tecnico.md`, sección 6.3.
