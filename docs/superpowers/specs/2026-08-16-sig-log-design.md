# SIG-LOG — Sistema Integral de Gestión Logística
## Documento de diseño

| | |
|---|---|
| **Proyecto** | SIG-LOG — Sistema Integral de Gestión Logística |
| **Asignatura** | Extracción del conocimiento en bases de datos (9° cuatrimestre) |
| **Programa** | Ingeniería en Desarrollo y Gestión de Software |
| **Autor** | Ludwin García |
| **Fecha** | 16 de agosto de 2026 |
| **Entrega** | 18 de agosto de 2026 |
| **Modalidad** | Individual |

---

## 1. Contexto y problema

Una empresa de transporte y distribución de mercancías opera una flotilla que
realiza entregas diarias a distintos clientes y destinos. Hoy la información de
vehículos, operadores, clientes, rutas, entregas, combustible y mantenimiento
está dispersa en archivos y sistemas separados.

Esa dispersión impide responder preguntas operativas y estratégicas:

| # | Pregunta del caso de estudio |
|---|---|
| P1 | ¿Qué rutas son más utilizadas? |
| P2 | ¿Qué vehículos generan mayores costos? |
| P3 | ¿Qué operadores realizan más entregas? |
| P4 | ¿Qué rutas presentan mayores retrasos? |
| P5 | ¿Qué vehículos consumen más combustible? |
| P6 | ¿Cuáles son las causas principales de retraso? |
| P7 | ¿Qué vehículos requieren mantenimiento? |
| P8 | ¿Es posible predecir si una entrega llegará tarde? |
| P9 | ¿Podemos identificar grupos de rutas similares? |
| P10 | ¿Cuáles son los horarios de mayor saturación y la demanda por servicio? |

## 2. Objetivo

Diseñar e implementar un sistema de información que administre vehículos,
operadores, clientes, rutas, entregas, combustible y mantenimiento, y que
genere información útil para optimizar las operaciones logísticas y apoyar la
toma de decisiones.

El sistema debe permitir identificar patrones de demanda de servicios, servicio
con mayor demanda, horarios de mayor saturación, frecuencia y rutas con mayor
número de envíos.

### 2.1 Alcance comprometido

Dentro del alcance:

- Los ocho módulos obligatorios, todos operativos.
- Data warehouse dimensional poblado por un proceso ETL de tres fases.
- Cuatro modelos de minería de datos (dos supervisados, dos no supervisados).
- Dashboard con cinco vistas analíticas.
- Manual de usuario y manual técnico, más un documento por unidad temática.

Fuera del alcance:

- Autenticación por roles y permisos granulares (se usa el sistema de usuarios
  de Django con un único perfil administrador).
- Geolocalización en tiempo real y mapas interactivos.
- Aplicación móvil.
- Despliegue en la nube.
- Segundo agrupamiento sobre clientes (marcado como opcional en §7.3).

### 2.2 Criterios de éxito

1. `python manage.py migrate && seed_demo && run_etl && train_models && runserver`
   levanta el sistema completo desde cero en una máquina limpia.
2. Los ocho módulos permiten alta, consulta, edición y baja.
3. El DW contiene las siete dimensiones y los tres hechos, poblados, con
   bitácora de ejecución consultable.
4. El clasificador de retrasos supera 0.75 de F1 en el conjunto de prueba.
5. El agrupamiento de rutas alcanza un coeficiente de silueta superior a 0.40.
6. Las diez preguntas del caso de estudio se responden desde el dashboard.

## 3. Decisiones de arquitectura

| Decisión | Elección | Razón |
|---|---|---|
| Lenguaje y framework | Python 3.13 + Django 5.1 | Un solo lenguaje para CRUD, ETL y minería de datos. |
| Base de datos | PostgreSQL 18 | Ya instalado y en ejecución; soporta múltiples esquemas en una base. |
| Interfaz | Django Templates + Bootstrap 5 | Monolito renderizado en servidor: menos piezas, más rápido de documentar con capturas. |
| Minería de datos | scikit-learn 1.8 | Cubre regresión, clasificación, PCA y K-means con una sola API. |
| Gráficas del dashboard | Chart.js | Interactivo, sin dependencias de compilación. |
| Gráficas de diagnóstico | matplotlib | Herramienta correcta para matriz de confusión, codo, silueta y residuales; además el temario la nombra explícitamente. |
| Datos | Generador sintético con patrones sembrados | Garantiza que los modelos tengan señal aprendible y clusters separables. |
| Documentación | Markdown en `docs/` | Versionado en git, convertible a PDF si se requiere. |

### 3.1 Convenciones

- **Código en inglés**: modelos, campos, funciones, clases, ramas y commits.
- **Interfaz y documentación en español**: etiquetas, mensajes, manuales.
- Cada entidad hereda de `BaseModel` con `created_at`, `updated_at`, `is_active`.
- Claves naturales legibles (`code`, `folio`, `plate`, `employee_number`) además
  de la llave primaria autoincremental.

### 3.2 Separación por capas

| Capa | Archivo | Responsabilidad | Prohibido |
|---|---|---|---|
| Views | `views.py` | Protocolo HTTP, enrutamiento, contexto, redirecciones | Reglas de negocio, consultas complejas |
| Forms | `forms.py` | Validación estricta y transformación de la entrada | Persistencia con efectos secundarios |
| Services | `services.py` | Lógica de negocio, cálculos, transacciones multi-entidad | Conocer `request` o `HttpResponse` |
| Models | `models.py` | Comportamiento inherente de la entidad, propiedades derivadas | Orquestar otras entidades |

En Django sin Django REST Framework, `forms.py` cumple el papel que los
serializers cumplen en una API: validación estricta y transformación de datos.

`services.py` solo se crea en los módulos que tienen algo que calcular. Crear
un servicio vacío en cada app sería una abstracción sin dominio que la
justifique.

### 3.3 Estructura del repositorio

```
SIG_LOG/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── core/               BaseModel, CrudViewSet, navegación, plantillas base
│   ├── customers/          M1  Clientes
│   ├── vehicles/           M2  Vehículos
│   ├── operators/          M3  Operadores
│   ├── routes/             M4  Rutas
│   ├── deliveries/         M5  Entregas
│   ├── fuel/               M6  Combustible
│   ├── maintenance/        M7  Mantenimiento
│   └── analytics/          M8  Reportes y análisis
│
├── warehouse/
│   ├── models.py           dimensiones y hechos (esquema dw)
│   ├── etl/
│   │   ├── extract.py
│   │   ├── transform.py
│   │   ├── cleaning.py
│   │   └── load.py
│   └── management/commands/run_etl.py
│
├── ml/
│   ├── datasets.py         construcción de matrices desde el DW
│   ├── supervised.py       regresión lineal + clasificación
│   ├── unsupervised.py     PCA + K-means
│   ├── evaluation.py       métricas y figuras de diagnóstico
│   ├── artifacts/          modelos entrenados (.joblib)
│   └── management/commands/train_models.py
│
├── seed/
│   └── management/commands/seed_demo.py
│
├── templates/
├── static/
└── docs/
```

`warehouse/` y `ml/` viven fuera de `apps/` porque no son módulos de negocio
con URLs propias: son infraestructura analítica. El módulo `analytics` es su
único consumidor y quien los expone al usuario. Esa frontera materializa la
separación entre el sistema transaccional y el sistema analítico.

### 3.4 El CRUD genérico

`apps/core/views.py` expone un `CrudViewSet` que genera lista con búsqueda y
paginación, alta, edición y baja lógica a partir de tres declaraciones:
el modelo, el formulario y las columnas a listar.

```python
class CustomerCrud(CrudViewSet):
    model = Customer
    form_class = CustomerForm
    list_columns = ["code", "business_name", "city", "customer_type"]
    search_fields = ["code", "business_name", "tax_id"]
    verbose_name_es = "Cliente"
```

Sin esto, siete módulos de captura significan treinta y cinco vistas y
veintiocho plantillas casi idénticas. Con esto, cada módulo son unas cuarenta
líneas. Es DRY aplicado donde de verdad paga.

## 4. Modelo de datos transaccional (esquema `public`)

### 4.1 Customer — M1 Clientes

| Campo | Tipo | Notas |
|---|---|---|
| `code` | CharField(10) | único, `CLI-0001` |
| `business_name` | CharField(150) | |
| `tax_id` | CharField(13) | RFC |
| `contact_name` | CharField(120) | |
| `phone` | CharField(20) | |
| `email` | EmailField | |
| `address` | CharField(200) | |
| `city` | CharField(80) | |
| `state` | CharField(80) | |
| `postal_code` | CharField(5) | |
| `customer_type` | CharField(12) | PREMIUM / REGULAR / OCCASIONAL |

Comportamiento: `total_deliveries`, `delivery_frequency`.

### 4.2 Vehicle — M2 Vehículos

| Campo | Tipo | Notas |
|---|---|---|
| `plate` | CharField(10) | único |
| `economic_number` | CharField(10) | único |
| `brand`, `model` | CharField(60) | |
| `year` | PositiveSmallIntegerField | |
| `vehicle_type` | CharField(10) | TRUCK / VAN / TRAILER / PICKUP |
| `cargo_capacity_kg` | DecimalField(10,2) | |
| `fuel_type` | CharField(10) | DIESEL / GASOLINE |
| `tank_capacity_l` | DecimalField(8,2) | |
| `current_odometer_km` | DecimalField(12,2) | |
| `acquisition_date` | DateField | |
| `status` | CharField(16) | AVAILABLE / ON_ROUTE / IN_MAINTENANCE / OUT_OF_SERVICE |

Comportamiento: `age_years`, `km_since_last_service`, `needs_maintenance`.

### 4.3 Operator — M3 Operadores

| Campo | Tipo | Notas |
|---|---|---|
| `employee_number` | CharField(10) | único |
| `first_name`, `last_name` | CharField(80) | |
| `license_number` | CharField(20) | |
| `license_type` | CharField(2) | A / B / C / E (federal) |
| `license_expiry` | DateField | |
| `hire_date` | DateField | |
| `phone` | CharField(20) | |
| `status` | CharField(12) | ACTIVE / VACATION / INACTIVE |

Comportamiento: `full_name`, `license_is_valid`, `seniority_years`.

### 4.4 Route — M4 Rutas

| Campo | Tipo | Notas |
|---|---|---|
| `code` | CharField(10) | único, `RUT-001` |
| `name` | CharField(150) | |
| `origin_city`, `destination_city` | CharField(80) | |
| `distance_km` | DecimalField(8,2) | |
| `estimated_duration_min` | PositiveIntegerField | |
| `route_type` | CharField(10) | LOCAL / REGIONAL / FORANEA |
| `zone` | CharField(40) | |
| `toll_cost` | DecimalField(10,2) | |

Comportamiento: `estimated_average_speed`.

### 4.5 Delivery — M5 Entregas

Entidad central. Su grano define el grano del hecho principal del DW.

| Campo | Tipo | Notas |
|---|---|---|
| `folio` | CharField(14) | único, `ENT-2026-00001` |
| `customer` | FK → Customer | PROTECT |
| `route` | FK → Route | PROTECT |
| `vehicle` | FK → Vehicle | PROTECT |
| `operator` | FK → Operator | PROTECT |
| `delay_cause` | FK → DelayCause | nullable, PROTECT |
| `scheduled_departure` | DateTimeField | |
| `actual_departure` | DateTimeField | nullable |
| `scheduled_arrival` | DateTimeField | |
| `actual_arrival` | DateTimeField | nullable |
| `cargo_weight_kg` | DecimalField(10,2) | |
| `packages_count` | PositiveIntegerField | |
| `declared_value` | DecimalField(12,2) | |
| `freight_cost` | DecimalField(10,2) | |
| `status` | CharField(12) | SCHEDULED / IN_TRANSIT / DELIVERED / DELAYED / CANCELLED |

Comportamiento: `delay_minutes`, `is_delayed`, `transit_minutes`, `on_time`.

Índices: `(scheduled_departure)`, `(route, scheduled_departure)`,
`(vehicle, scheduled_departure)`, `(status)`.

### 4.6 DelayCause — catálogo

| Campo | Tipo |
|---|---|
| `code` | CharField(20) único |
| `name` | CharField(80) |
| `category` | CharField(10) — EXTERNA / INTERNA / MECANICA |

Valores iniciales: TRÁFICO, CLIMA, FALLA MECÁNICA, DOCUMENTACIÓN,
CARGA/DESCARGA, ACCIDENTE, OTRO, NO ESPECIFICADA.

Este catálogo es lo que convierte P6 en una consulta en lugar de una conjetura.

### 4.7 FuelLoad — M6 Combustible

| Campo | Tipo | Notas |
|---|---|---|
| `folio` | CharField(14) | único |
| `vehicle` | FK → Vehicle | PROTECT |
| `operator` | FK → Operator | PROTECT |
| `delivery` | FK → Delivery | nullable, SET_NULL |
| `load_datetime` | DateTimeField | |
| `station_name` | CharField(120) | |
| `liters` | DecimalField(8,2) | > 0 |
| `price_per_liter` | DecimalField(6,2) | > 0 |
| `total_cost` | DecimalField(10,2) | calculado |
| `odometer_km` | DecimalField(12,2) | |

Comportamiento: `km_traveled` (contra la carga anterior del mismo vehículo),
`efficiency_km_per_liter`.

### 4.8 Maintenance — M7 Mantenimiento

| Campo | Tipo | Notas |
|---|---|---|
| `folio` | CharField(14) | único |
| `vehicle` | FK → Vehicle | PROTECT |
| `maintenance_type` | CharField(12) | PREVENTIVE / CORRECTIVE |
| `service_date` | DateField | |
| `odometer_km` | DecimalField(12,2) | |
| `description` | TextField | |
| `workshop` | CharField(120) | |
| `labor_cost`, `parts_cost` | DecimalField(10,2) | |
| `total_cost` | DecimalField(10,2) | calculado |
| `next_service_km` | DecimalField(12,2) | |
| `days_out_of_service` | PositiveSmallIntegerField | |
| `status` | CharField(12) | SCHEDULED / IN_PROGRESS / COMPLETED |

### 4.9 Servicios de negocio

| Servicio | Responsabilidad |
|---|---|
| `deliveries.services.register_arrival(delivery, arrival_at, cause=None)` | Calcula el retraso, exige causa si llegó tarde, cambia el estado y libera el vehículo. Una sola transacción atómica. |
| `vehicles.services.maintenance_alerts()` | Vehículos que cruzaron `next_service_km` o llevan más de seis meses sin servicio. Responde P7 en tiempo real. |
| `fuel.services.efficiency_report(period)` | Rendimiento km/L por vehículo entre cargas consecutivas. Alimenta P5. |

Las alertas de mantenimiento se calculan sobre el OLTP, **no** sobre el DW. Un
almacén se recarga por lotes y «¿qué vehículo necesita servicio hoy?» es una
pregunta operativa, no analítica. Mezclarlas sería el error que la Unidad II
enseña a evitar.

## 5. Data warehouse (Unidad II)

### 5.1 Tres esquemas en una base

```
public   →  OLTP     los 8 módulos, escritura en vivo
staging  →  landing  extracción cruda, sin transformar
dw       →  estrella dimensiones, hechos y bitácoras
```

Los modelos del DW declaran `db_table = 'dw"."dim_route'`, de modo que
`migrate` crea las tablas en su esquema y el ORM sigue disponible para las
consultas del dashboard. Una migración inicial de `warehouse` ejecuta
`CREATE SCHEMA IF NOT EXISTS staging` y `CREATE SCHEMA IF NOT EXISTS dw`
antes de cualquier otra operación.

Es una solución pragmática y de uso extendido. La alternativa formal sería un
router de bases de datos con `search_path` por alias; se descarta porque
duplica configuración sin aportar nada en este alcance.

### 5.2 Dimensiones

| Tabla | Clave natural | Atributos |
|---|---|---|
| `dim_date` | `date_key` (YYYYMMDD) | año, trimestre, mes, nombre de mes, semana, día, nombre de día, quincena, `is_weekend`, `is_holiday` |
| `dim_time` | `time_key` (0–23) | hora, `time_band`: MADRUGADA / PICO_AM / MEDIODIA / PICO_PM / NOCHE |
| `dim_customer` | `code` | razón social, ciudad, estado, tipo de cliente |
| `dim_vehicle` | `plate` | número económico, marca, modelo, año, tipo, `age_range`, `capacity_range` |
| `dim_operator` | `employee_number` | nombre completo, tipo de licencia, `seniority_range` |
| `dim_route` | `code` | nombre, origen, destino, km, `distance_range`, tipo, zona |
| `dim_delay_cause` | `code` | nombre, categoría |

`dim_time` existe porque «horarios de mayor saturación» es un patrón que el
caso de estudio pide de forma explícita. Sin una dimensión de hora, esa
pregunta se contesta con `EXTRACT()` disperso por todo el código.

### 5.3 Hechos

```
fact_delivery      grano: una entrega
  dimensiones: date_key, time_key, customer_key, route_key,
               vehicle_key, operator_key, delay_cause_key
  medidas:     cargo_weight_kg, packages_count, freight_cost,
               planned_duration_min, actual_duration_min,
               delay_minutes, is_delayed (0/1), distance_km, cost_per_km

fact_fuel          grano: una carga de combustible
  dimensiones: date_key, time_key, vehicle_key, operator_key
  medidas:     liters, price_per_liter, total_cost,
               km_traveled, efficiency_km_per_liter

fact_maintenance   grano: un servicio
  dimensiones: date_key, vehicle_key
  medidas:     labor_cost, parts_cost, total_cost,
               days_out_of_service, odometer_km
```

Tres hechos y no uno solo porque los granos son distintos: una entrega, una
carga de combustible y un servicio de mantenimiento no ocurren juntos.
Forzarlos a una sola tabla produciría filas con la mitad de las medidas nulas,
que es el error clásico al aprender modelado dimensional.

Se elige **modelo estrella** sobre copo de nieve: las dimensiones quedan
desnormalizadas, las consultas del dashboard requieren un solo JOIN por
dimensión y el esquema es más fácil de explicar. El costo —redundancia en
atributos como ciudad o marca— es irrelevante a esta escala.

### 5.4 Proceso ETL

**Fase 1 — Extract** (`warehouse/etl/extract.py`)

Lee del OLTP y vuelca a `staging.stg_*` sin modificar los datos. Dos tipos de
extracción:

- **Completa** (`--full`): trunca staging y arrastra todo el histórico.
- **Incremental** (por defecto): solo filas con `updated_at` posterior a la
  última corrida exitosa registrada en `dw.etl_log`.

**Fase 2 — Transform** (`warehouse/etl/transform.py`, `cleaning.py`)

Cada técnica de limpieza es una función con nombre propio y prueba asociada:

| Técnica | Aplicación |
|---|---|
| Normalización | `TRIM`, mayúsculas en catálogos, placas sin guiones, RFC en mayúsculas |
| Tratamiento de nulos | Causa de retraso ausente → `NO_ESPECIFICADA`; ciudad vacía → `DESCONOCIDA` |
| Deduplicación | Por clave natural, conservando el registro más reciente |
| Validación de rango | `liters > 0`, `distance_km > 0`, `freight_cost >= 0` |
| Coherencia temporal | `actual_arrival >= actual_departure`; fechas dentro de la ventana del proyecto |
| Integridad referencial | La entrega apunta a cliente, ruta, vehículo y operador existentes |
| Detección de atípicos | Rendimiento fuera de `[1.0, 8.0]` km/L → cuarentena, no eliminación |
| Derivación | `delay_minutes`, `is_delayed`, `time_band`, buckets de antigüedad y distancia |

Regla invariable: **nada se descarta en silencio**. Cada fila rechazada se
escribe en `dw.etl_error` con la regla que la rechazó y su carga original.

**Fase 3 — Load** (`warehouse/etl/load.py`)

- Dimensiones: *upsert* por clave natural, SCD tipo 1 (sobrescribe el valor
  anterior). Se documenta como decisión consciente: SCD tipo 2 exigiría
  vigencias y versionado que este alcance no justifica.
- `dim_date` y `dim_time` se generan una sola vez a partir del rango de fechas.
- Hechos: `bulk_create` por lotes, resolviendo llaves surrogate contra las
  dimensiones ya cargadas.
- Una transacción por fase: si el load falla, el DW no queda a medias.

### 5.5 Bitácoras

```
dw.etl_log     run_id, phase, table_name, started_at, finished_at,
               rows_read, rows_written, rows_rejected, status, message

dw.etl_error   run_id, source_table, source_pk, rule, description,
               raw_payload, detected_at
```

### 5.6 Interfaz de línea de comandos

```
python manage.py run_etl              extracción incremental
python manage.py run_etl --full       extracción completa, sin vaciar el DW
python manage.py run_etl --rebuild    vacía dimensiones y hechos, luego --full
```

`--rebuild` implica `--full`: primero trunca las tablas de `dw` y `staging`, y
después ejecuta las tres fases sobre todo el histórico. Combinar `--rebuild`
con `--full` es válido pero redundante.

## 6. Generador de datos sintéticos

`python manage.py seed_demo --months 18 [--seed 42]`

Volumen real producido por la corrida de referencia (`--months 18 --seed 42`),
medido contra la base de datos:

| Entidad | Registros | Origen de la cifra |
|---|---|---|
| Clientes | 120 | fijo |
| Vehículos | 50 | fijo |
| Operadores | 40 | fijo |
| Rutas | 60 | fijo (24 urbanas + 22 regionales + 14 foráneas) |
| Entregas | 27 158 cerradas | volumen mensual por arquetipo de ruta |
| Cargas de combustible | 3 633 | una cada 4 a 11 días por vehículo (72.7 por unidad) |
| Mantenimientos | 565 | 11.3 por vehículo en 18 meses |

Tasas de retraso medidas en esa corrida:

| Grupo | Entregas | Tasa de retraso |
|---|---|---|
| Zonas congestionadas (METROPOLITANA, ORIENTE) | 17 586 | **0.6792** |
| Resto de zonas | 9 572 | **0.1107** |
| Global | 27 158 | 0.4788 |

Los tres últimos renglones se derivan de las fórmulas del generador, no se fijan
a mano: cambiar los rangos de los arquetipos o el intervalo de recarga mueve las
cifras. Una corrida completa tarda menos de diez segundos.

Patrones sembrados de forma deliberada, para que los modelos tengan señal
aprendible en lugar de ruido:

1. Las zonas METROPOLITANA y ORIENTE concentran los retrasos. El patrón se
   ancla a la **zona**, no a rutas individuales, porque `zone` es una variable
   del modelo y la identidad de la ruta también: si la congestión viviera solo
   en objetos de ruta concretos y el clasificador no viera identidad, el patrón
   sería inaprendible.
2. Los vehículos de más de ocho años consumen más y fallan con mayor frecuencia.
3. Las salidas en franjas pico (07–09 h y 17–19 h) acumulan más retraso.
4. El perfil agregado de rutas produce grupos separables en tres o cuatro
   conglomerados.
5. Los clientes PREMIUM concentran mayor frecuencia y volumen.
6. La distribución de causas de retraso sigue un Pareto, no una uniforme.

Se fija una semilla aleatoria para que el conjunto sea reproducible: los
resultados del documento coinciden con los que obtiene quien reproduce el
proyecto.

El generador inyecta además una proporción controlada de registros sucios
(nulos, duplicados, valores fuera de rango, incoherencias de fecha) para que
las técnicas de limpieza de la Unidad II tengan sobre qué actuar y la bitácora
de errores muestre resultados reales.

## 7. Minería de datos

### 7.1 Unidad III — Análisis supervisado

**Modelo A · Clasificación de retraso** — responde P8.

Variable objetivo: `is_delayed` (binaria).

Dos algoritmos comparados:

- **Regresión logística**, como línea base interpretable: permite leer el peso
  de cada variable.
- **Random Forest**, como retador: captura interacciones (ruta × franja horaria
  × antigüedad del vehículo) y entrega importancia de variables.

Se elige por F1 sobre el conjunto de prueba y la elección se justifica por
escrito.

Métricas: accuracy, precision, recall, F1, matriz de confusión, ROC-AUC.

**Modelo B · Regresión de minutos de retraso**

Variable objetivo: `delay_minutes` (continua). Algoritmo: regresión lineal
múltiple, que es el que la unidad enseña.

Métricas: **MSE** (error cuadrático medio) y **MAE** (error absoluto medio),
que son las dos que el temario nombra explícitamente, más **RMSE** y R² para
poder interpretarlas en las unidades del problema.

**Variables predictoras** (ambos modelos):

`distance_km`, `planned_duration_min`, `cargo_weight_kg`, `packages_count`,
`time_band`, `day_of_week`, `route_type`, `zone`, `vehicle_age_range`,
`vehicle_type`, `operator_seniority_range`, `customer_type`.

**Exclusiones por fuga de datos.** Quedan fuera `actual_departure`,
`actual_arrival`, `status` y `delay_cause`: son conocidas solo *después* del
hecho. Incluirlas daría una exactitud cercana al 100 % y un modelo sin ningún
valor predictivo. Esta exclusión se documenta explícitamente porque es el error
que un evaluador busca primero.

**Protocolo.** Preprocesamiento dentro de un `Pipeline` de scikit-learn
(`StandardScaler` para numéricas, `OneHotEncoder(handle_unknown="ignore")` para
categóricas), de modo que el escalado se ajuste solo con el conjunto de
entrenamiento y el artefacto `.joblib` sea autocontenido. Partición 80/20
estratificada, más validación cruzada de cinco pliegues sobre entrenamiento.

### 7.2 Unidad IV — Análisis no supervisado

**Agrupamiento de rutas** — responde P9.

Perfil por ruta, agregado desde el DW: distancia, duración media, tasa de
retraso, retraso promedio, entregas por mes, peso promedio, costo por km y
rendimiento medio de combustible.

- **PCA** → reducción a dos componentes, con reporte de varianza explicada.
  Cumple dos funciones: elimina la correlación entre distancia y duración, y
  hace graficable el resultado en un plano.
- **K-means** → barrido de k de 2 a 10, eligiendo con **método del codo** y
  **coeficiente de silueta**. Ese barrido es el «entrenamiento, prueba y error»
  del temario, hecho de forma medible.
- Cada conglomerado recibe una **etiqueta interpretable** derivada de su perfil
  («rutas foráneas eficientes», «rutas urbanas congestionadas», «rutas de bajo
  volumen»). Un cluster sin nombre no es conocimiento extraído; es un número.

Métricas: inercia, coeficiente de silueta, índice de Davies-Bouldin.

### 7.3 Opcional

Un segundo K-means sobre clientes (frecuencia, volumen, valor) si el tiempo lo
permite. **No forma parte del alcance comprometido.**

### 7.4 Comando de entrenamiento

```
python manage.py train_models
```

Entrena los modelos, guarda los artefactos en `ml/artifacts/`, genera las
figuras de diagnóstico en `static/ml/` y escribe un reporte de métricas en
`docs/U3_Analisis_Supervisado.md` y `docs/U4_Analisis_No_Supervisado.md`.

## 8. Módulo 8 — Reportes y análisis (Unidad V)

| Vista | Contenido | Preguntas |
|---|---|---|
| `/analytics/` | KPIs: entregas del período, porcentaje a tiempo, retraso promedio, costo total, km recorridos, rendimiento medio. Tendencia mensual de entregas y costos. | P10 |
| `/analytics/operations/` | Top rutas por volumen · top operadores por entregas · mapa de calor día × hora · Pareto de causas de retraso | P1, P3, P4, P6, P10 |
| `/analytics/costs/` | Costo por vehículo (combustible vs mantenimiento, barras apiladas) · rendimiento km/L por vehículo · costo por km por ruta | P2, P5 |
| `/analytics/maintenance-alerts/` | Vehículos que requieren servicio, con semáforo por urgencia | P7 |
| `/analytics/predictions/` | Formulario de predicción de retraso + reporte de evaluación del modelo | P8 |
| `/analytics/clusters/` | Dispersión PCA coloreada por conglomerado + tabla de perfil por grupo | P9 |

Todo reporte tabular se exporta a CSV y Excel mediante pandas.

**División de herramientas gráficas.** Chart.js renderiza el dashboard web
(interactivo, adecuado para la defensa). matplotlib genera las figuras de
diagnóstico de los modelos: matriz de confusión, curva del codo, gráfico de
silueta, dispersión PCA y gráfico de residuales. No es trabajo duplicado —
matplotlib es la herramienta correcta para diagnóstico y su presencia en el
repositorio satisface el entregable de código de la Unidad V.

## 9. Manejo de errores

| Situación | Respuesta |
|---|---|
| Validación de formulario | Mensaje en español junto al campo; no se persiste nada |
| Violación de regla de negocio en un servicio | Excepción de dominio, capturada en la vista y mostrada como alerta |
| Fila inválida durante el ETL | Se registra en `dw.etl_error`; el proceso continúa |
| Fallo de fase del ETL | `rollback` de la transacción; `dw.etl_log` marca `FAILED` con el mensaje |
| Modelo no entrenado al pedir predicción | La vista informa que debe ejecutarse `train_models` |
| DW vacío al abrir el dashboard | Estado vacío con instrucción de ejecutar `run_etl` |

## 10. Pruebas

Alcance proporcional al tiempo disponible: pruebas donde un error sería
silencioso y caro, no cobertura por cobertura.

| Objetivo | Prueba |
|---|---|
| `cleaning.py` | Una prueba por regla de limpieza, con caso válido e inválido |
| `deliveries.services.register_arrival` | Cálculo de retraso, exigencia de causa, liberación del vehículo |
| `fuel.services.efficiency_report` | Rendimiento entre cargas consecutivas, incluida la primera carga sin previa |
| `vehicles.services.maintenance_alerts` | Umbral por kilometraje y por antigüedad |
| `ml/datasets.py` | Ausencia de columnas con fuga de datos en la matriz de entrenamiento |
| ETL de extremo a extremo | Sembrar, ejecutar, verificar conteos y contenido de bitácoras |

## 11. Documentación entregable

```
README.md                        arranque en cinco comandos
docs/Manual_Usuario.md           un capítulo por módulo, con capturas
docs/Manual_Tecnico.md           instalación, arquitectura, despliegue, mantenimiento
docs/Arquitectura.md             capas, diagramas, decisiones de diseño
docs/Diccionario_Datos.md        cada tabla y campo, OLTP y DW
docs/U1_Analisis_Metodologia.md  comparativo IA/ML/DM/Big Data, CRISP-DM, planeación
docs/U2_Data_Warehouse.md        esquema, fuentes, limpieza, parámetros
docs/U3_Analisis_Supervisado.md  justificación, diseño, evaluación, optimización
docs/U4_Analisis_No_Supervisado.md
docs/U5_Visualizacion.md         gráficas e interpretación de resultados
```

Los manuales se escriben para alguien que nunca vio el sistema: desde instalar
PostgreSQL hasta interpretar un conglomerado.

## 12. Cobertura de las cinco unidades

| Unidad | Exigencia del temario | Dónde se cumple |
|---|---|---|
| I. Introducción al análisis de datos | Comparativo IA/ML/DM/Big Data; objetivo y alcance; justificación de metodología; planeación de etapas | `docs/U1_Analisis_Metodologia.md` |
| II. Preparación de los datos | Esquema de data warehouse; tipos y fuentes; técnicas de limpieza; parámetros; conjunto preprocesado en repositorio | `warehouse/`, `docs/U2_Data_Warehouse.md`, esquemas `staging` y `dw` |
| III. Análisis supervisado | Justificación del algoritmo; diseño del modelo; reporte de evaluación y optimización; modelos en repositorio | `ml/supervised.py`, `ml/artifacts/`, `docs/U3_…` |
| IV. Análisis no supervisado | Justificación; resultados; evaluación y optimización; modelos de agrupación y reducción de dimensionalidad | `ml/unsupervised.py`, `docs/U4_…` |
| V. Presentación y visualización | Dashboard con gráficas personalizadas; interpretación de resultados; código de gráficas en repositorio | `apps/analytics/`, `ml/evaluation.py`, `docs/U5_…` |

## 13. Orden de construcción

Cada paso deja el sistema en un estado ejecutable y demostrable. Si el tiempo
se corta, lo construido funciona.

1. **Esqueleto** — proyecto Django, `config/`, conexión a PostgreSQL, `apps/core/`
   con `BaseModel` y `CrudViewSet`, plantilla base con navegación.
2. **Módulos de captura** — los siete modelos, formularios, CRUD y catálogo de
   causas de retraso.
3. **Generador sintético** — `seed_demo` con los patrones sembrados.
4. **Data warehouse** — esquemas, dimensiones, hechos, bitácoras y las tres
   fases del ETL.
5. **Minería de datos** — `datasets.py`, modelos supervisados y no supervisados,
   `train_models`, figuras de diagnóstico.
6. **Dashboard** — las seis vistas de `analytics` y las exportaciones.
7. **Documentación** — manuales y documentos por unidad.

## 14. Riesgos

| Riesgo | Mitigación |
|---|---|
| El clasificador no alcanza F1 de 0.75 | Los patrones sembrados garantizan señal; si falla, se ajusta la fuerza del patrón en el generador y se documenta el ajuste |
| El agrupamiento no separa (silueta < 0.40) | El generador construye los perfiles de ruta alrededor de centros distinguibles |
| `db_table` con esquema da problemas en migraciones | Alternativa lista: crear las tablas del DW con `RunSQL` y consultarlas con `pandas.read_sql` |
| El tiempo se agota | El orden de construcción prioriza lo evaluable; los módulos de captura salen del CRUD genérico en un solo bloque |

## 15. Requisitos de entorno

Verificados en la máquina de desarrollo:

| Componente | Versión | Estado |
|---|---|---|
| Python | 3.13.14 | instalado |
| Django | 5.1.2 | instalado |
| scikit-learn | 1.8.0 | instalado |
| pandas | 2.3.3 | instalado |
| PostgreSQL | 18 | servicio en ejecución |
| git | 2.52.0 | instalado |
| `psycopg[binary]` | — | **pendiente de instalar** |
| matplotlib, openpyxl, python-dotenv, Faker | — | **pendientes de instalar** |

Credenciales de base de datos en `.env`, fuera del control de versiones, con
`.env.example` como plantilla.
