# Unidad II — Preparación de los datos: el data warehouse

## 1. Esquema del data warehouse

Modelo **estrella**: siete dimensiones desnormalizadas y tres tablas de
hechos, en el esquema `dw` de la misma base PostgreSQL que el OLTP (ver
decisión de arquitectura en `docs/Arquitectura.md`, secciones 1 y 3).

```
                dim_date        dim_time
                    \               /
   dim_customer ── fact_delivery ── dim_route
                     /      |      \
              dim_vehicle   |    dim_operator
                             \
                       dim_delay_cause

   dim_vehicle ── fact_fuel ── dim_operator      (+ dim_date, dim_time)
   dim_vehicle ── fact_maintenance                (+ dim_date)
```

### 1.1 Las siete dimensiones

| Dimensión | Clave natural | Atributos |
|---|---|---|
| `dim_date` | `date_key` (YYYYMMDD) | año, trimestre, mes, nombre de mes, semana, día, nombre de día, quincena, `is_weekend` |
| `dim_time` | `time_key` (0–23) | hora, `time_band` |
| `dim_customer` | `code` | razón social, ciudad, estado, tipo de cliente |
| `dim_vehicle` | `plate` | número económico, marca, modelo, año, tipo, `age_range`, `capacity_range` |
| `dim_operator` | `employee_number` | nombre completo, tipo de licencia, `seniority_range` |
| `dim_route` | `code` | nombre, origen, destino, km, `distance_range`, tipo, zona |
| `dim_delay_cause` | `code` | nombre, categoría |

`dim_time` existe porque "horarios de mayor saturación" (P10) es una
pregunta explícita del caso de estudio. Sin una dimensión de hora dedicada,
esa pregunta se resolvería con `EXTRACT(HOUR FROM ...)` disperso en cada
consulta del dashboard.

### 1.2 Las tres tablas de hechos

```
fact_delivery      grano: una entrega
  dimensiones: date_key, time_key, customer_key, route_key,
               vehicle_key, operator_key, delay_cause_key
  medidas:     cargo_weight_kg, packages_count, freight_cost,
               planned_duration_min, actual_duration_min,
               delay_minutes, is_delayed, distance_km, cost_per_km

fact_fuel          grano: una carga de combustible
  dimensiones: date_key, time_key, vehicle_key, operator_key
  medidas:     liters, price_per_liter, total_cost,
               km_traveled, efficiency_km_per_liter

fact_maintenance   grano: un servicio de taller
  dimensiones: date_key, vehicle_key
  medidas:     labor_cost, parts_cost, total_cost,
               days_out_of_service, odometer_km
```

**Por qué tres hechos y no uno solo:** los tres granos son distintos — una
entrega, una carga de combustible y una orden de servicio no ocurren juntas
ni tienen la misma cardinalidad (26,886 entregas contra 3,624 cargas y 566
servicios en la corrida de referencia). Forzarlas a una tabla única
produciría filas con la mitad de las medidas nulas cada vez que un evento
de un tipo no coincidiera con uno de otro tipo, que es precisamente el
error que el modelado dimensional enseña a evitar. Justificación completa
de estrella sobre copo de nieve en `docs/Arquitectura.md`, sección 3.

## 2. Tipos y fuentes de datos

Las ocho tablas fuente viven en el esquema `public` (OLTP) y son, en su
totalidad, **datos estructurados**: filas con esquema fijo en una base
relacional, sin texto libre no tipado ni archivos binarios que integrar. No
hay en este proyecto datos semiestructurados (JSON de un servicio externo,
por ejemplo) ni no estructurados (imágenes, texto libre de un sensor); el
único campo de texto libre es `Maintenance.description`, y no participa en
ningún modelo ni en ninguna limpieza más allá de copiarse tal cual.

| Tabla fuente | Registros (corrida de referencia) |
|---|---|
| `customers_customer` | 120 |
| `vehicles_vehicle` | 50 |
| `operators_operator` | 40 |
| `routes_route` | 60 |
| `deliveries_delivery` | 27,218 |
| `fuel_fuelload` | 3,644 |
| `maintenance_maintenance` | 566 |
| `deliveries_delaycause` | 8 |

### 2.1 Dos tipos de extracción

- **Incremental** (por defecto, `python manage.py run_etl`): solo se
  extraen filas cuyo `updated_at` es posterior al `finished_at` de la
  última corrida de Load exitosa. Es el modo normal de operación: una
  corrida diaria u horaria que solo procesa lo que cambió.
- **Completa** (`--full`): se vacía la landing zone (`staging.stg_*`) y se
  arrastra todo el histórico del OLTP. Se usa la primera vez que se puebla
  el almacén, o cuando se sospecha que una corrida incremental dejó algo
  fuera.
- **Reconstrucción** (`--rebuild`): implica `--full` y además vacía
  dimensiones y hechos en `dw` antes de cargar. Es la que se usó para
  producir todas las cifras de este documento.

## 3. Técnicas de limpieza de datos

Cada técnica es una función con nombre propio en `warehouse/etl/cleaning.py`,
con su propia prueba unitaria (caso válido e inválido) en
`warehouse/tests/test_cleaning.py`. La regla invariable del proceso: **nada
se descarta en silencio** — cada fila rechazada se escribe en
`dw.etl_error` con la regla que la rechazó y el registro original completo.

| Técnica | Qué detecta | Qué hace | Filas rechazadas (corrida de referencia) |
|---|---|---|---|
| Normalización (`normalize_text`, `normalize_code`, `normalize_plate`) | Espacios sobrantes, minúsculas, placas con guiones | Corrige el valor; no rechaza filas | 0 (corrección silenciosa, no cuarentena) |
| Tratamiento de nulos (`default_if_blank`) | Ciudad vacía en clientes o rutas | La reemplaza por `DESCONOCIDA`; en causa de retraso ausente, por `NO_ESPECIFICADA` | 0 (sustitución, no rechazo) |
| Deduplicación | Clave natural repetida (folio, código, placa) dentro de la misma extracción | Conserva el registro más reciente por `extracted_at` en siete de las ocho tablas de staging; rechaza los demás. `stg_fuel_load` es la excepción: ordena por `(vehicle_plate, load_datetime)` en lugar de `extracted_at`, para no romper la cadena de odómetro por vehículo | incluido en el desglose por regla si aplica; en la corrida de referencia no hubo duplicados que forzaran rechazo |
| Validación de rango (`is_positive`, `is_non_negative`) | Litros ≤ 0, distancia ≤ 0, flete o costo negativo | Rechaza la fila | **`is_positive`: 10** (cargas de combustible con litros ≤ 0) · **`is_non_negative`: 8** (entregas con flete negativo) |
| Coherencia temporal (`dates_are_coherent`) | Llegada real anterior a la salida | Rechaza la fila | **272** (entregas) |
| Integridad referencial | La entrega, carga o mantenimiento referencia un cliente, ruta, vehículo, operador o causa que no existe en la extracción limpia | Rechaza la fila | 0 en la corrida de referencia (la generación sintética no produce huérfanos) |
| Detección de atípicos (`is_efficiency_outlier`) | Rendimiento fuera de `[1.0, 12.0]` km/L | Pone la fila en cuarentena, **no la elimina del origen** | **10** (cargas de combustible) |
| Exclusión de entregas abiertas (`open_delivery`) | Entrega sin `actual_arrival` (todavía en curso) | Se excluye del hecho — solo entregas cerradas tienen grano de hecho | **52** |
| Derivación (`age_range`, `distance_range`, `capacity_range`, `seniority_range`, `delay_minutes`, `is_delayed`, `time_band`) | — | Calcula columnas nuevas a partir de las existentes | No aplica (no es una regla de rechazo) |

Total de filas en cuarentena en la corrida de referencia (`--months 18 --seed 42`, ver `docs/_datos_medidos.md`):

```
stg_delivery  | dates_are_coherent    |  272
stg_delivery  | open_delivery         |   52
stg_fuel_load | is_efficiency_outlier |   10
stg_fuel_load | is_positive           |   10
stg_delivery  | is_non_negative       |    8
```

Esto explica la diferencia entre lo extraído y lo cargado:
27,218 entregas extraídas → 26,886 en `fact_delivery` (332 rechazadas:
272 + 52 + 8); 3,644 cargas de combustible extraídas → 3,624 en `fact_fuel`
(20 rechazadas: 10 + 10).

**Sobre el límite `[1.0, 12.0]` km/L:** el generador sintético
(`seed/patterns.py::BASE_EFFICIENCY`) fija el rendimiento base de una
pick-up en 8.10 km/L, con hasta ±8% de variación aleatoria — una pick-up
sana puede llegar a 8.75 km/L. Un límite superior anterior de 8.0 km/L
ponía en cuarentena el 40% de las cargas de pick-up sanas, un falso
positivo masivo. El límite vigente (12.0) sigue capturando las anomalías
reales, que en la práctica se miden en cientos de km/L cuando ocurren.
Cualquiera que ajuste `BASE_EFFICIENCY` debe revisar `EFFICIENCY_BOUNDS` en
el mismo cambio, porque ambos valores están acoplados por este argumento.

## 4. Parámetros de configuración

| Parámetro | Valor | Dónde se define |
|---|---|---|
| Esquemas | `public`, `staging`, `dw` | `warehouse/migrations/0001_create_schemas.py` |
| Tamaño de lote (`BATCH_SIZE`) | 2000 filas | `warehouse/etl/extract.py`, `warehouse/etl/load.py` |
| Tipo de SCD en dimensiones | Tipo 1 (sobrescritura) | `warehouse/etl/load.py::_load_dimension` |
| `EFFICIENCY_BOUNDS` | `[1.0, 12.0]` km/L | `warehouse/etl/cleaning.py` |
| `DELAY_TOLERANCE_MINUTES` | 15 minutos | `apps/deliveries/models.py`, `warehouse/etl/transform.py`, `seed/management/commands/seed_demo.py` (duplicado deliberadamente en los tres lugares, ver sección 4.1) |
| Conexión a la base | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | `.env`, leídos en `config/settings.py` |
| Flags de `run_etl` | `--full`, `--rebuild` | `warehouse/management/commands/run_etl.py` |

### 4.1 Sobre `DELAY_TOLERANCE_MINUTES` en tres lugares

La misma constante —15 minutos— está implementada de forma independiente
en `apps/deliveries/models.py` (`Delivery.is_delayed`), en
`warehouse/etl/transform.py` (cálculo de `is_delayed` para `fact_delivery`)
y en el generador sintético (`seed/management/commands/seed_demo.py`,
`is_late = extra > 15`). Las tres deben coincidir: si el OLTP marca una
entrega como retrasada y el ETL la marca como puntual (o viceversa), el
almacén contradice al sistema transaccional del que se supone que deriva.
Una entrega exactamente 15 minutos tarde **no** se considera retrasada en
ninguna de las tres implementaciones.

## 5. Evidencia de una corrida exitosa — `dw.etl_log`

```
   phase   |    table_name    | rows_read | rows_written | rows_rejected | status
-----------+------------------+-----------+--------------+---------------+--------
 EXTRACT   | stg_customer     |       120 |          120 |             0 | SUCCESS
 EXTRACT   | stg_delay_cause  |         8 |            8 |             0 | SUCCESS
 EXTRACT   | stg_delivery     |     27218 |        27218 |             0 | SUCCESS
 EXTRACT   | stg_fuel_load    |      3644 |         3644 |             0 | SUCCESS
 EXTRACT   | stg_maintenance  |       566 |          566 |             0 | SUCCESS
 EXTRACT   | stg_operator     |        40 |           40 |             0 | SUCCESS
 EXTRACT   | stg_route        |        60 |           60 |             0 | SUCCESS
 EXTRACT   | stg_vehicle      |        50 |           50 |             0 | SUCCESS
 TRANSFORM | stg_customer     |       120 |          120 |             0 | SUCCESS
 TRANSFORM | stg_delay_cause  |         8 |            8 |             0 | SUCCESS
 TRANSFORM | stg_delivery     |     27218 |        26886 |           332 | SUCCESS
 TRANSFORM | stg_fuel_load    |      3644 |         3624 |            20 | SUCCESS
 TRANSFORM | stg_maintenance  |       566 |          566 |             0 | SUCCESS
 TRANSFORM | stg_operator     |        40 |           40 |             0 | SUCCESS
 TRANSFORM | stg_route        |        60 |           60 |             0 | SUCCESS
 TRANSFORM | stg_vehicle      |        50 |           50 |             0 | SUCCESS
 LOAD      | dim_customer     |       120 |          120 |             0 | SUCCESS
 LOAD      | dim_date         |         0 |          546 |             0 | SUCCESS
 LOAD      | dim_delay_cause  |         8 |            8 |             0 | SUCCESS
 LOAD      | dim_operator     |        40 |           40 |             0 | SUCCESS
 LOAD      | dim_route        |        60 |           60 |             0 | SUCCESS
 LOAD      | dim_time         |         0 |           24 |             0 | SUCCESS
 LOAD      | dim_vehicle      |        50 |           50 |             0 | SUCCESS
 LOAD      | fact_delivery    |     26886 |        26886 |             0 | SUCCESS
 LOAD      | fact_fuel        |      3624 |         3624 |             0 | SUCCESS
 LOAD      | fact_maintenance |       566 |          566 |             0 | SUCCESS
(26 filas)
```

Volumen final del almacén: `dim_date` 546, `dim_time` 24, `dim_customer`
120, `dim_vehicle` 50, `dim_operator` 40, `dim_route` 60, `dim_delay_cause`
8, `fact_delivery` 26,886, `fact_fuel` 3,624, `fact_maintenance` 566.

Cómo leer y auditar estas bitácoras (incluidas las consultas SQL) está en
`docs/Manual_Tecnico.md`, sección 6.3, junto con el comportamiento cuando la
fase Load falla a la mitad: las filas `SUCCESS` por tabla revierten con los
datos (describirían trabajo deshecho), pero sobrevive una única fila
`dw.etl_log` con `phase="LOAD"`, `status="FAILED"` y el detalle de la
excepción, escrita fuera de la transacción una vez que ya revirtió.
