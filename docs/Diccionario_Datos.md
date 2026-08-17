# Diccionario de Datos — SIG-LOG

Inventario generado contra la base `siglog` en ejecución
(`information_schema.columns`, esquemas `public`, `staging` y `dw`,
excluyendo las tablas internas de Django y de autenticación). Los tipos y la
nulidad son los reales de PostgreSQL; el significado y el ejemplo se añaden
a mano a partir del modelo de Django correspondiente.

## Esquema `public` — OLTP

### customers_customer (Cliente)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 1 |
| created_at | timestamp with time zone | No | Fecha de alta del registro | 2025-01-15 10:00:00-06 |
| updated_at | timestamp with time zone | No | Fecha de la última modificación | 2025-06-01 09:30:00-06 |
| is_active | boolean | No | Baja lógica | true |
| code | character varying | No | Código único del cliente | CLI-0001 |
| business_name | character varying | No | Razón social | Distribuidora del Bajío S.A. de C.V. |
| tax_id | character varying | No | RFC, en mayúsculas | DBA010101AB1 |
| contact_name | character varying | No | Nombre de la persona de contacto | Juan Pérez |
| phone | character varying | No | Teléfono a 10 dígitos | 4421234567 |
| email | character varying | No | Correo (puede quedar vacío) | contacto@empresa.com |
| address | character varying | No | Dirección | Av. Reforma 123 |
| city | character varying | No | Ciudad | Querétaro |
| state | character varying | No | Estado | Querétaro |
| postal_code | character varying | No | Código postal | 76000 |
| customer_type | character varying | No | PREMIUM / REGULAR / OCCASIONAL | PREMIUM |

### vehicles_vehicle (Vehículo)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 7 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| plate | character varying | No | Placa, sin guiones ni espacios | ABC0007 |
| economic_number | character varying | No | Número económico único | EC-0007 |
| brand | character varying | No | Marca | Kenworth |
| model | character varying | No | Modelo | T680 |
| year | smallint | No | Año del vehículo | 2019 |
| vehicle_type | character varying | No | TRUCK / VAN / TRAILER / PICKUP | TRAILER |
| cargo_capacity_kg | numeric | No | Capacidad de carga en kilogramos | 22000.00 |
| fuel_type | character varying | No | DIESEL / GASOLINE | DIESEL |
| tank_capacity_l | numeric | No | Capacidad de tanque en litros | 450.00 |
| current_odometer_km | numeric | No | Odómetro actual | 185340.00 |
| acquisition_date | date | No | Fecha de adquisición | 2019-03-15 |
| next_service_km | numeric | No | Kilometraje del próximo servicio | 190000.00 |
| last_service_date | date | Sí | Fecha del último servicio | 2026-04-02 |
| status | character varying | No | AVAILABLE / ON_ROUTE / IN_MAINTENANCE / OUT_OF_SERVICE | AVAILABLE |

### operators_operator (Operador)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 12 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| employee_number | character varying | No | Número de empleado único | OP-0012 |
| first_name | character varying | No | Nombre | María |
| last_name | character varying | No | Apellidos | González López |
| license_number | character varying | No | Número de licencia | LF-04821 |
| license_type | character varying | No | A / B / C / E | C |
| license_expiry | date | No | Vigencia de la licencia | 2027-11-30 |
| hire_date | date | No | Fecha de ingreso | 2020-02-01 |
| phone | character varying | No | Teléfono | 5512345678 |
| status | character varying | No | ACTIVE / VACATION / INACTIVE | ACTIVE |

### routes_route (Ruta)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 33 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| code | character varying | No | Código único de ruta | RUT-033 |
| name | character varying | No | Nombre descriptivo (origen — destino) | Querétaro — León |
| origin_city | character varying | No | Ciudad de origen | Querétaro |
| destination_city | character varying | No | Ciudad de destino | León |
| distance_km | numeric | No | Distancia planeada | 175.00 |
| estimated_duration_min | integer | No | Duración estimada en minutos | 172 |
| route_type | character varying | No | LOCAL / REGIONAL / FORANEA | REGIONAL |
| zone | character varying | No | Zona operativa | BAJIO |
| toll_cost | numeric | No | Costo de casetas | 210.00 |

### deliveries_delaycause (Causa de retraso)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 1 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| code | character varying | No | Código único | TRAFICO |
| name | character varying | No | Nombre en español | Tráfico |
| category | character varying | No | EXTERNA / INTERNA / MECANICA | EXTERNA |

### deliveries_delivery (Entrega)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 20145 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| folio | character varying | No | Folio único | ENT-2026-00001 |
| scheduled_departure | timestamp with time zone | No | Salida programada | 2026-03-02 07:00:00-06 |
| actual_departure | timestamp with time zone | Sí | Salida real (nula si no ha salido) | 2026-03-02 07:05:00-06 |
| scheduled_arrival | timestamp with time zone | No | Llegada programada | 2026-03-02 08:35:00-06 |
| actual_arrival | timestamp with time zone | Sí | Llegada real (nula si sigue abierta) | 2026-03-02 09:20:00-06 |
| cargo_weight_kg | numeric | No | Peso de la carga | 1850.00 |
| packages_count | integer | No | Número de bultos | 42 |
| declared_value | numeric | No | Valor declarado de la mercancía | 92500.00 |
| freight_cost | numeric | No | Flete cobrado | 1128.75 |
| status | character varying | No | SCHEDULED / IN_TRANSIT / DELIVERED / DELAYED / CANCELLED | DELAYED |
| customer_id | bigint | No | FK → customers_customer (PROTECT) | 1 |
| delay_cause_id | bigint | Sí | FK → deliveries_delaycause (PROTECT); nula si no hubo retraso | 1 |
| operator_id | bigint | No | FK → operators_operator (PROTECT) | 12 |
| route_id | bigint | No | FK → routes_route (PROTECT) | 33 |
| vehicle_id | bigint | No | FK → vehicles_vehicle (PROTECT) | 7 |

### fuel_fuelload (Carga de combustible)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 3055 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| folio | character varying | No | Folio único | COM-003055 |
| load_datetime | timestamp with time zone | No | Fecha y hora de la carga | 2026-03-10 08:00:00-06 |
| station_name | character varying | No | Estación | Pemex León |
| liters | numeric | No | Litros cargados | 380.00 |
| price_per_liter | numeric | No | Precio por litro | 24.85 |
| total_cost | numeric | No | Costo total (calculado) | 9443.00 |
| odometer_km | numeric | No | Odómetro al momento de la carga | 186100.00 |
| delivery_id | bigint | Sí | FK → deliveries_delivery (SET_NULL); opcional | null |
| operator_id | bigint | No | FK → operators_operator (PROTECT) | 12 |
| vehicle_id | bigint | No | FK → vehicles_vehicle (PROTECT) | 7 |

### maintenance_maintenance (Mantenimiento)

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno | 480 |
| created_at / updated_at | timestamp with time zone | No | Auditoría | — |
| is_active | boolean | No | Baja lógica | true |
| folio | character varying | No | Folio único | MTO-000480 |
| maintenance_type | character varying | No | PREVENTIVE / CORRECTIVE | CORRECTIVE |
| service_date | date | No | Fecha del servicio | 2026-02-18 |
| odometer_km | numeric | No | Odómetro al momento del servicio | 184500.00 |
| description | text | No | Descripción del trabajo | Reparación de transmisión |
| workshop | character varying | No | Taller | Taller Central |
| labor_cost | numeric | No | Mano de obra | 4200.00 |
| parts_cost | numeric | No | Refacciones | 15800.00 |
| total_cost | numeric | No | Costo total (calculado) | 20000.00 |
| next_service_km | numeric | Sí | Próximo kilometraje de servicio | 194500.00 |
| days_out_of_service | smallint | No | Días fuera de servicio | 3 |
| status | character varying | No | SCHEDULED / IN_PROGRESS / COMPLETED | COMPLETED |
| vehicle_id | bigint | No | FK → vehicles_vehicle (PROTECT) | 7 |

## Esquema `staging` — landing zone del ETL

Las ocho tablas comparten tres columnas de procedencia:

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint | No | Identificador interno de la fila de staging | 88231 |
| run_id | uuid | No | Identificador de la corrida del ETL que la generó | a1b2c3d4-... |
| source_id | bigint | Sí | `id` del registro origen en `public` | 20145 |
| extracted_at | timestamp with time zone | No | Momento en que Extract copió la fila | 2026-08-17 04:35:00-06 |

El resto de columnas de cada `stg_*` son una copia **sin transformar** de
los campos de negocio de su tabla origen, declaradas como `text` (o
`numeric`/`date`/`boolean` sin restricción de nulidad) precisamente porque
la landing zone acepta lo que la fuente produjo, defectos incluidos:
`stg_customer`, `stg_vehicle`, `stg_operator`, `stg_route`,
`stg_delay_cause`, `stg_delivery`, `stg_fuel_load`, `stg_maintenance`. Su
definición completa está en `warehouse/models.py`; el detalle de qué
columna alimenta a cuál del OLTP está en `warehouse/etl/extract.py`.

## Esquema `dw` — almacén dimensional

### dim_date

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| date_key | integer (PK) | No | Clave natural `YYYYMMDD` | 20260302 |
| full_date | date | No | Fecha calendario | 2026-03-02 |
| year / quarter / month / week / day | smallint | No | Partes de la fecha | 2026 / 1 / 3 / 9 / 2 |
| month_name | character varying | No | Nombre del mes en español | Marzo |
| day_of_week | smallint | No | Día de la semana, 0 = lunes | 0 |
| day_name | character varying | No | Nombre del día en español | Lunes |
| fortnight | smallint | No | Quincena (1 o 2) | 1 |
| is_weekend | boolean | No | Sábado o domingo | false |

### dim_time

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| time_key | smallint (PK) | No | Hora del día, 0–23 | 7 |
| hour | smallint | No | Hora (igual a `time_key`) | 7 |
| time_band | character varying | No | Franja horaria (ver enumeraciones) | PICO_AM |

### dim_customer / dim_vehicle / dim_operator / dim_route / dim_delay_cause

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| *_key (PK) | bigint | No | Llave surrogate autogenerada | 7 |
| code / plate / employee_number | character varying | No | Clave natural, única | RUT-033 |
| Atributos descriptivos | character varying / numeric | No | Copia limpia de la dimensión (ver tabla de atributos en `docs/U2_Data_Warehouse.md`) | — |
| Atributos derivados (`age_range`, `distance_range`, `capacity_range`, `seniority_range`) | character varying | No | Bucket calculado en Transform (ver enumeraciones) | 4-8 |

### fact_delivery

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint (PK) | No | Identificador interno | 26886 |
| folio | character varying | No | Folio de la entrega, único | ENT-2026-00001 |
| date_id | integer | No | FK → dim_date | 20260302 |
| time_id | smallint | No | FK → dim_time | 7 |
| customer_id / route_id / vehicle_id / operator_id | bigint | No | FK → dimensión respectiva | — |
| delay_cause_id | bigint | Sí | FK → dim_delay_cause; nula si no hubo retraso | 1 |
| cargo_weight_kg | numeric | No | Peso de la carga | 1850.00 |
| packages_count | integer | No | Número de bultos | 42 |
| freight_cost | numeric | No | Flete | 1128.75 |
| planned_duration_min | integer | No | Duración planeada | 172 |
| actual_duration_min | integer | No | Duración real | 205 |
| delay_minutes | integer | No | Minutos de retraso (0 si llegó a tiempo) | 45 |
| is_delayed | smallint | No | 1 si `delay_minutes > 15`, si no 0 | 1 |
| distance_km | numeric | No | Distancia de la ruta | 175.00 |
| cost_per_km | numeric | No | `freight_cost / distance_km` | 6.4500 |

### fact_fuel

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint (PK) | No | Identificador interno | 3624 |
| folio | character varying | No | Folio de la carga, único | COM-003055 |
| date_id | integer | No | FK → dim_date | 20260310 |
| time_id | smallint | No | FK → dim_time | 8 |
| vehicle_id / operator_id | bigint | No | FK → dimensión respectiva | — |
| liters | numeric | No | Litros cargados | 380.00 |
| price_per_liter | numeric | No | Precio por litro | 24.85 |
| total_cost | numeric | No | Costo total | 9443.00 |
| km_traveled | numeric | Sí | Kilómetros desde la carga anterior del mismo vehículo | 950.00 |
| efficiency_km_per_liter | numeric | Sí | Rendimiento (nulo si no hay carga previa) | 2.16 |

### fact_maintenance

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint (PK) | No | Identificador interno | 566 |
| folio | character varying | No | Folio de la orden, único | MTO-000480 |
| date_id | integer | No | FK → dim_date | 20260218 |
| vehicle_id | bigint | No | FK → dim_vehicle | 7 |
| maintenance_type | character varying | No | PREVENTIVE / CORRECTIVE | CORRECTIVE |
| labor_cost / parts_cost / total_cost | numeric | No | Costos | 4200.00 / 15800.00 / 20000.00 |
| days_out_of_service | smallint | No | Días fuera de servicio | 3 |
| odometer_km | numeric | No | Odómetro al servicio | 184500.00 |

### etl_log

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint (PK) | No | Identificador interno | 104 |
| run_id | uuid | No | Identificador de la corrida | a1b2c3d4-... |
| phase | character varying | No | EXTRACT / TRANSFORM / LOAD | LOAD |
| table_name | character varying | No | Tabla afectada en esa fase | fact_delivery |
| started_at | timestamp with time zone | No | Inicio de la fase para esa tabla | 2026-08-17 04:38:05-06 |
| finished_at | timestamp with time zone | Sí | Fin de la fase (nulo si sigue corriendo o falló antes de cerrar) | 2026-08-17 04:38:09-06 |
| rows_read / rows_written / rows_rejected | integer | No | Conteos de la fase | 27218 / 26886 / 332 |
| status | character varying | No | RUNNING / SUCCESS / FAILED | SUCCESS |
| message | text | No | Detalle del error si `status = FAILED` | "" |

### etl_error

| Columna | Tipo | Nulo | Significado | Ejemplo |
|---|---|---|---|---|
| id | bigint (PK) | No | Identificador interno | 9931 |
| run_id | uuid | No | Corrida que detectó el rechazo | a1b2c3d4-... |
| source_table | character varying | No | Tabla de staging de origen | stg_delivery |
| source_pk | character varying | No | Folio o clave del registro rechazado | ENT-2026-14032 |
| rule | character varying | No | Regla de limpieza que rechazó la fila | dates_are_coherent |
| description | text | No | Explicación en español | La llegada real es anterior a la salida. |
| raw_payload | jsonb | No | Copia del registro original ofensor | {"folio": "...", "actual_arrival": "..."} |
| detected_at | timestamp with time zone | No | Momento de la detección | 2026-08-17 04:37:40-06 |

## Enumeraciones

| Campo | Valores |
|---|---|
| `customer_type` | PREMIUM, REGULAR, OCCASIONAL |
| `vehicle_type` | TRUCK, VAN, TRAILER, PICKUP |
| `fuel_type` | DIESEL, GASOLINE |
| `Vehicle.status` | AVAILABLE, ON_ROUTE, IN_MAINTENANCE, OUT_OF_SERVICE |
| `Operator.status` | ACTIVE, VACATION, INACTIVE |
| `Delivery.status` | SCHEDULED, IN_TRANSIT, DELIVERED, DELAYED, CANCELLED |
| `Maintenance.status` | SCHEDULED, IN_PROGRESS, COMPLETED |
| `license_type` | A (Automovilista), B (Chofer), C (Carga federal), E (Doble remolque) |
| `route_type` | LOCAL, REGIONAL, FORANEA |
| `maintenance_type` | PREVENTIVE, CORRECTIVE |
| `delay_cause.category` | EXTERNA, INTERNA, MECANICA |
| `time_band` | MADRUGADA (0–5 h), MANANA (6 h), PICO_AM (7–9 h), MEDIODIA (10–16 h), PICO_PM (17–19 h), NOCHE (20–23 h) |
| `age_range` (vehículo) | 0-3, 4-8, 9+ (años) |
| `distance_range` (ruta) | CORTA (< 80 km), MEDIA (80–349 km), LARGA (≥ 350 km) |
| `capacity_range` (vehículo) | LIGERA (< 2,000 kg), MEDIANA (2,000–14,999 kg), PESADA (≥ 15,000 kg) |
| `seniority_range` (operador) | 0-2, 3-5, 6+ (años) |
