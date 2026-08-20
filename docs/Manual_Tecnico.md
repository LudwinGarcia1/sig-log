# Manual Técnico — SIG-LOG

## 1. Arquitectura general

Tres esquemas en una sola base PostgreSQL:

```
public   →  OLTP     los 8 módulos de negocio, escritura en vivo
staging  →  landing  extracción cruda del ETL, sin transformar
dw       →  estrella dimensiones, hechos y bitácoras
```

Y cuatro capas dentro de cada módulo de negocio:

| Capa | Archivo | Responsabilidad | Prohibido |
|---|---|---|---|
| Views | `views.py` | Protocolo HTTP, enrutamiento, contexto, redirecciones | Reglas de negocio, consultas complejas |
| Forms | `forms.py` | Validación estricta y transformación de la entrada | Persistencia con efectos secundarios |
| Services | `services.py` | Lógica de negocio, cálculos, transacciones multi-entidad | Conocer `request` o `HttpResponse` |
| Models | `models.py` | Comportamiento inherente de la entidad, propiedades derivadas | Orquestar otras entidades |

El razonamiento detrás de cada decisión de arquitectura —por qué tres
esquemas y no un router de bases de datos, por qué estrella y no copo de
nieve, por qué SCD tipo 1— está en `docs/Arquitectura.md`. Este manual se
concentra en cómo operar el sistema.

## 2. Requisitos e instalación

| Componente | Versión verificada |
|---|---|
| Python | 3.13.14 |
| Django | 5.1.2 |
| scikit-learn | 1.8.0 |
| pandas | 2.3.3 |
| PostgreSQL | 18 |
| git | 2.52.0 |

### 2.1 Instalar PostgreSQL 18 en Windows

1. Descarga el instalador desde `postgresql.org/download/windows` y
   ejecútalo. Durante la instalación:
   - Elige el puerto por defecto, `5432`.
   - Define una contraseña para el superusuario `postgres` (la necesitarás
     una sola vez, para crear el rol dedicado).
   - Instala también "Command Line Tools" — trae `psql` y `createdb`, que
     este manual usa más adelante.
2. Verifica que el servicio quedó activo:

```powershell
Get-Service postgresql-x64-18
```

3. Crea el rol de aplicación y su base, **nunca conectando como
   `postgres` en producción**:

```sql
CREATE ROLE siglog LOGIN PASSWORD 'una-contraseña-fuerte' CREATEDB;
CREATE DATABASE siglog OWNER siglog;
```

Puedes ejecutar ese bloque con `psql -U postgres -h localhost` o, más
simple, crear la base ya con el rol vía `createdb`:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres -h localhost siglog
```

y luego otorgarle la propiedad al rol `siglog` desde `psql`.

### 2.2 Instalar el proyecto

```powershell
git clone <url> SIG_LOG; cd SIG_LOG
conda create -n siglog python=3.13 -y
conda activate siglog
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` con las credenciales del rol `siglog` y ejecuta la puesta en
marcha descrita en el `README.md` raíz.

### 2.3 Crear el usuario de acceso

El sistema completo está detrás de una sesión, así que después de `migrate`
hay que crear al menos un usuario:

```powershell
python manage.py createsuperuser
```

El comando pide usuario, correo y contraseña de forma interactiva. No hay
credenciales en el repositorio a propósito: quien instala el sistema define
las suyas. El mismo usuario sirve para el sitio y para `/admin/`.

## 3. Configuración

Todas las variables viven en `.env` (fuera de control de versiones;
`.env.example` es la plantilla) y se leen en `config/settings.py` con
`python-dotenv`.

| Variable | Significado | Valor por defecto |
|---|---|---|
| `DB_NAME` | Nombre de la base de datos | `siglog` |
| `DB_USER` | Rol de conexión | `siglog` |
| `DB_PASSWORD` | Contraseña del rol | `changeme` (cámbiala) |
| `DB_HOST` | Host de PostgreSQL | `localhost` |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DJANGO_SECRET_KEY` | Clave de firma de Django | clave insegura de desarrollo si se omite |
| `DJANGO_DEBUG` | Modo de depuración | `True` |

### 3.1 Control de acceso

`config/settings.py` declara `LOGIN_URL = "/entrar/"`,
`LOGIN_REDIRECT_URL = "/"` y `LOGOUT_REDIRECT_URL = "/entrar/"` como rutas
literales, no como nombres de URL: el urlconf reducido que usan las pruebas
del motor CRUD no declara la vista de acceso, y un nombre por resolver las
rompería.

La protección entra por dos lugares y nada más:

| Punto | Qué cubre |
|---|---|
| `LoginRequiredMixin` en `CrudContextMixin` (`apps/core/views.py`) | Las cuatro vistas CRUD de los siete módulos de captura |
| `@login_required` | Las seis pantallas de `apps/analytics/views.py`, la exportación, `delivery_arrival` y `HomeView` |

Un visitante anónimo recibe 302 hacia `/entrar/?next=<ruta>`, así que después
de firmar aterriza en la pantalla que pidió.

El sistema nunca se conecta como `postgres`: `DATABASES["default"]["USER"]`
en `config/settings.py` toma el valor de `DB_USER`, que en todo entorno
documentado es `siglog`.

## 4. Estructura del código

```
apps/
  core/         BaseModel (created_at, updated_at, is_active), CrudConfig y las
                cuatro vistas genéricas, navegación declarativa, plantillas base
  customers/    M1 — Cliente
  vehicles/     M2 — Vehículo, y vehicles.services.maintenance_alerts
  operators/    M3 — Operador
  routes/       M4 — Ruta
  deliveries/   M5 — Delivery, DelayCause, deliveries.services.register_arrival
  fuel/         M6 — FuelLoad, fuel.services.efficiency_report
  maintenance/  M7 — Maintenance, maintenance.services.complete_maintenance
  analytics/    M8 — queries.py (una función por pregunta del caso de estudio),
                views.py, exports.py (CSV/Excel/PDF), forms.py (formulario de predicción)

warehouse/      Modelos de staging y dw, y el ETL de tres fases (etl/)
ml/             Matrices de datos, modelos supervisados y no supervisados,
                figuras de diagnóstico, comando train_models
seed/           Generador de datos sintéticos y los patrones que siembra
```

`warehouse/` y `ml/` no tienen URLs propias: son infraestructura analítica que
solo `apps/analytics` consume y expone. Ningún otro módulo importa de ellos.

## 5. El motor CRUD genérico

`apps/core/views.py` define `CrudConfig`, que a partir de tres declaraciones
genera las cuatro vistas de un módulo de captura (lista con búsqueda y
paginación, alta, edición, baja lógica) y sus cuatro rutas.

**Agregar un noveno módulo — ejemplo completo** (un catálogo hipotético de
"Almacenes"):

```python
# apps/warehouses/models.py
from django.db import models
from apps.core.models import BaseModel

class Warehouse(BaseModel):
    code = models.CharField("Código", max_length=10, unique=True)
    name = models.CharField("Nombre", max_length=150)
    city = models.CharField("Ciudad", max_length=80)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


# apps/warehouses/forms.py
from django import forms
from apps.warehouses.models import Warehouse

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ["code", "name", "city"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
        }


# apps/warehouses/views.py
from apps.core.views import CrudConfig
from apps.warehouses.forms import WarehouseForm
from apps.warehouses.models import Warehouse

class WarehouseCrud(CrudConfig):
    model = Warehouse
    form_class = WarehouseForm
    list_columns = ["code", "name", "city"]
    search_fields = ["code", "name"]
    label = "Almacén"
    label_plural = "Almacenes"
    slug = "warehouse"


# apps/warehouses/urls.py
from apps.core.navigation import register
from apps.warehouses.views import WarehouseCrud

urlpatterns = WarehouseCrud.urlpatterns()
register("warehouse_list", "Almacenes")
```

Falta registrar la app en `INSTALLED_APPS`, incluir sus URLs en
`config/urls.py` (`path("almacenes/", include("apps.warehouses.urls"))`) y
correr `makemigrations` / `migrate`. Con eso el módulo completo —lista,
alta, edición, baja lógica, buscador, paginación y entrada en la barra de
navegación— queda funcionando en menos de cuarenta líneas de código propio,
sin tocar plantillas.

## 6. El proceso ETL

Tres fases, cada una registrada en `dw.etl_log` con un contador de filas
leídas, escritas y rechazadas (`warehouse/etl/context.py`, clase `EtlRun`).

### 6.1 Fases

1. **Extract** (`warehouse/etl/extract.py`) — copia cada tabla del OLTP a su
   tabla `staging.stg_*` sin transformar nada. Dos modalidades:
   - **Incremental** (por defecto): solo filas con `updated_at` posterior a
     la fecha de finalización de la última corrida `LOAD` exitosa.
   - **Completa** (`--full`): vacía cada tabla de staging y arrastra todo el
     histórico.
2. **Transform** (`warehouse/etl/transform.py`, `cleaning.py`) — limpia,
   valida, deriva columnas y **rechaza** filas defectuosas, nunca las
   descarta en silencio: cada rechazo se escribe en `dw.etl_error` con la
   regla que lo causó (tabla 6.2).
3. **Load** (`warehouse/etl/load.py`) — upsert de dimensiones por clave
   natural (SCD tipo 1: se sobrescribe el valor anterior) y `bulk_create` de
   los tres hechos. Toda la fase corre dentro de una única
   `@transaction.atomic`.

### 6.2 Técnicas de limpieza

| Función (`cleaning.py`) | Qué hace | Dónde se aplica |
|---|---|---|
| `normalize_text` / `normalize_code` / `normalize_plate` | `TRIM`, mayúsculas, sin guiones ni espacios | Nombres, códigos, RFC, placas |
| `default_if_blank` | Ciudad vacía → `DESCONOCIDA` | Clientes y rutas |
| Deduplicación (en cada `_transform_*`) | Por clave natural, conserva el registro más reciente (`extracted_at` descendente) | Las ocho tablas |
| `is_positive` / `is_non_negative` | Rango de valores (litros, distancia, flete) | Rutas, entregas, combustible, mantenimiento |
| `dates_are_coherent` | La llegada real no puede preceder a la salida | Entregas |
| Integridad referencial | Cliente, ruta, vehículo, operador y causa deben existir | Entregas, combustible, mantenimiento |
| `is_efficiency_outlier` | Rendimiento fuera de `[1.0, 12.0]` km/L → cuarentena | Combustible |
| Derivación (`age_range`, `distance_range`, `capacity_range`, `seniority_range`, `delay_minutes`, `is_delayed`) | Categorías y medidas calculadas | Vehículos, rutas, operadores, entregas |

Detalle de conteos reales de rechazo por regla:
`docs/U2_Data_Warehouse.md`.

### 6.3 Leer `dw.etl_log` y `dw.etl_error`

```sql
SELECT phase, table_name, rows_read, rows_written, rows_rejected, status
FROM dw.etl_log ORDER BY started_at;

SELECT rule, COUNT(*) AS registros
FROM dw.etl_error GROUP BY rule ORDER BY 2 DESC;
```

La primera consulta muestra la secuencia completa de una corrida; la
segunda, qué regla está rechazando más filas. `dw.etl_error.raw_payload`
guarda el registro original completo, así que un rechazo siempre se puede
auditar sin volver al OLTP.

**Sobre el comportamiento de `run_id` ante un fallo:** el cuerpo de
`load.run` (`_load_all`) se ejecuta dentro de un único
`with transaction.atomic():`, así que si la fase Load falla a la mitad, la
base de datos revierte todo lo que esa fase intentaba escribir — y con ello
revierte también las filas `SUCCESS` por tabla que `EtlRun.phase()` había
creado dentro de esa transacción. Eso es intencional: esas filas describirían
trabajo que ya no existe, así que mantenerlas haría mentir a la bitácora.
Pero `load.run` envuelve ese bloque en un `try/except`: cuando la transacción
ya revirtió, escribe **fuera** de ella una única fila `dw.etl_log` con
`phase="LOAD"`, `table_name="(fase completa)"`, `status="FAILED"` y el
`message` con el tipo y texto de la excepción, y vuelve a lanzar la
excepción. El resultado: una corrida que falló en Load se reconoce porque
existen filas `EXTRACT`/`TRANSFORM` en `SUCCESS` para ese `run_id` y
exactamente una fila `LOAD` en `FAILED` que explica por qué — nunca ausencia
total de evidencia. El almacén nunca queda a medias (la transacción sigue
protegiendo eso) y además la bitácora nunca queda muda ante un fallo de Load.

### 6.4 Interfaz de línea de comandos

```powershell
python manage.py run_etl              # extracción incremental
python manage.py run_etl --full       # extracción completa, sin vaciar el DW
python manage.py run_etl --rebuild    # vacía dimensiones y hechos, luego --full
```

## 6.5 El filtro de periodo

Las seis pantallas de análisis y las ocho exportaciones se acotan a un rango
de fechas. El diseño tiene tres piezas y ninguna se repite:

| Pieza | Archivo | Responsabilidad |
|---|---|---|
| `Period` | `apps/analytics/queries.py` | Guarda el rango, con ambos extremos opcionales, y sabe describirse para la pantalla |
| `_scope()` | `apps/analytics/queries.py` | Aplica el filtro sobre `dim_date.full_date`, que está indexado |
| `PeriodForm` | `apps/analytics/forms.py` | Valida las dos fechas y resuelve los atajos |

Las nueve funciones de consulta reciben `period=None`; el filtro se escribe
una vez en `_scope()` y llega a cada tabla de hechos por `_deliveries()`,
`_fuel()` y `_maintenance()`. Un `Period()` sin límites se comporta igual que
no pasar periodo, así que la ruta sin parámetros sigue devolviendo el
histórico completo.

**Los atajos se anclan en `data_bounds()`, no en `date.today()`.** El almacén
puede terminar semanas atrás de la fecha del sistema —depende de cuándo se
corrió el último `run_etl`— y un "último mes" contado desde hoy devolvería
una pantalla vacía sin explicar por qué.

**El periodo viaja en la cadena de consulta**, no en la sesión. Por eso los
enlaces de exportación de las plantillas llevan `?{{ period_query }}`: un
archivo descargado contiene exactamente lo que estaba en pantalla, y una URL
con periodo se puede compartir o guardar en marcadores.

El caso de un rango sin datos está cubierto por
`test_an_empty_period_answers_zero_instead_of_crashing`: ninguna consulta
divide entre cero ni indexa una lista vacía.

## 7. Los modelos de minería

### 7.1 Pipelines

Clasificación y regresión comparten el mismo preprocesamiento, encapsulado en
`sklearn.pipeline.Pipeline` junto con el estimador:

```python
ColumnTransformer([
    ("num", StandardScaler(), NUMERIC_FEATURES),
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
])
```

Mantener el escalado dentro del pipeline significa que se ajusta solo con el
conjunto de entrenamiento y que el artefacto `.joblib` guardado ya incluye el
preprocesamiento — no hace falta ningún paso externo antes de predecir.

### 7.2 Por qué importa la exclusión de fuga de datos

`ml/datasets.py` declara `LEAKAGE_COLUMNS`: `actual_departure`,
`actual_arrival`, `status`, `delay_cause` (y las columnas derivadas de estas:
`delay_cause_code`, `actual_duration_min`, `delay_minutes`, `is_delayed` como
*features*, aunque `is_delayed` y `delay_minutes` sí son las variables
objetivo). Ninguna de ellas es conocida antes de que la entrega salga.
Incluirlas produciría una exactitud cercana al 100% y un modelo inútil en
producción, porque en el momento de predecir —antes de que el vehículo
salga— esos datos todavía no existen. `ml/tests/test_datasets.py` verifica
explícitamente que la matriz de entrenamiento no las contenga.

### 7.3 Reentrenar

```powershell
python manage.py train_models
python manage.py train_models --k 4          # fuerza el número de conglomerados
python manage.py train_models --random-state 7
```

Los artefactos se guardan en `ml/artifacts/` (`delay_classifier.joblib`,
`delay_regressor.joblib`, `route_clusters.joblib`, `metrics.json`) y las
figuras de diagnóstico en `static/ml/` (`confusion_matrix.png`,
`residuals.png`, `elbow.png`, `silhouette.png`, `pca_scatter.png`). Ninguno
de los dos directorios está pensado para editarse a mano.

## 8. Comandos de administración

| Comando | Flags | Efecto |
|---|---|---|
| `seed_demo` | `--months N` (por defecto 18) · `--seed N` (por defecto 42) · `--dirty-rate F` (por defecto 0.03) | Borra y regenera clientes, vehículos, operadores, rutas, entregas, combustible y mantenimiento con los patrones sembrados descritos en `docs/U1_Analisis_Metodologia.md`. Exige que el catálogo de causas ya exista (`loaddata delay_causes`). |
| `run_etl` | `--full` · `--rebuild` | Corre las tres fases del ETL. Sin flags, extracción incremental. |
| `train_models` | `--k N` · `--random-state N` | Entrena los cuatro modelos, guarda artefactos y figuras. |
| `createsuperuser` | — | Crea un usuario con acceso al sitio y a `/admin/`. Interactivo. |
| `changepassword` | `<usuario>` | Reasigna la contraseña de un usuario existente. |

## 9. Pruebas

```powershell
python manage.py test
```

227 pruebas repartidas así:

| Paquete | Enfoque |
|---|---|
| `apps/*` (119 pruebas) | Reglas de negocio por módulo: cálculo de retraso y exigencia de causa en `deliveries.services`, umbrales de `vehicles.services.maintenance_alerts`, rendimiento entre cargas consecutivas en `fuel.services`, cierre de orden en `maintenance.services`, el CRUD genérico, las respuestas de `analytics.queries` y el control de acceso de las quince pantallas (`apps/core/tests/test_authentication.py`). |
| `warehouse/tests/*` (57 pruebas) | Una prueba por técnica de limpieza con caso válido e inválido, extracción incremental y completa, carga de dimensiones y hechos, ETL de extremo a extremo. |
| `ml/tests/*` (38 pruebas) | Ausencia de columnas con fuga de datos, entrenamiento de ambos clasificadores y del regresor, barrido de k y elección del conglomerado, ejecución completa de `train_models`. |
| `seed/tests.py` (13 pruebas) | Volumen generado y que las tasas de retraso caigan dentro del rango realista que los patrones sembrados prometen. |

**Sobre `train_models` en las pruebas:** `TrainModelsCommandTest`,
`PredictionViewTest` y `UntrainedModelTest` (en `apps/analytics/tests.py`)
también ejecutan `train_models` o inspeccionan sus artefactos, y ese comando
escribe sobre rutas del sistema de archivos (`ml/artifacts/`, `static/ml/`),
no la base de datos de pruebas. Antes esto hacía que `python manage.py test`
sobrescribiera en silencio los modelos de producción con unos entrenados
sobre los tres o cuatro meses de datos de la fixture de prueba. Ya no: cada
una de esas pruebas usa `tempfile.TemporaryDirectory()` junto con
`unittest.mock.patch.object` sobre `ml.supervised.ARTIFACT_DIR`,
`CLASSIFIER_PATH`, `REGRESSOR_PATH`, `ml.unsupervised.CLUSTER_PATH` y
`ml.evaluation.FIGURE_DIR`/`METRICS_PATH`, de modo que cada entrenamiento de
prueba escribe en un directorio temporal y nunca en `ml/artifacts/` ni
`static/ml/`. Correr la suite completa ya no requiere volver a entrenar
después.

## 10. Mantenimiento y solución de problemas

| Situación | Causa probable | Solución |
|---|---|---|
| `migrate` falla mencionando el esquema `dw` o `staging` | La migración `warehouse.0001_create_schemas` no corrió | Ejecuta `python manage.py migrate warehouse 0001_create_schemas` y luego `migrate` de nuevo |
| El ETL rechaza (casi) todo | Regla de limpieza demasiado estricta para los datos reales, o catálogo de causas vacío | Revisa `dw.etl_error.rule` agrupado por conteo (consulta en la sección 6.3); si es `referential_integrity`, confirma que `loaddata delay_causes` corrió antes de `seed_demo` |
| El clasificador queda por debajo del umbral de F1 (0.75) | La señal sembrada en el generador es insuficiente para el volumen actual | Ver la mitigación de la especificación de diseño (§14): ajustar los coeficientes de `seed/patterns.py::delay_probability` y documentar el ajuste |
| El dashboard, predicción o conglomerados muestran datos obsoletos o peores de lo esperado | El almacén cambió (nuevo `run_etl`) desde el último `train_models`, o nunca se ejecutó | `python manage.py train_models` |
| `Error: That port is already in use` al hacer `runserver` | Otro proceso ocupa el puerto 8000 | `python manage.py runserver 8001`, o cierra el proceso que ocupa el 8000 |
| `django.db.utils.OperationalError: password authentication failed` | `.env` no coincide con las credenciales del rol `siglog` | Verifica `DB_USER`/`DB_PASSWORD` contra lo que creaste en PostgreSQL |

## 11. Despliegue

Este proyecto está pensado para demostración y evaluación académica, no para
producción. Si se necesitara exponerlo:

- `DJANGO_DEBUG=False` en `.env`.
- `ALLOWED_HOSTS` en `config/settings.py` debe incluir el dominio o IP real
  (hoy solo admite `localhost` y `127.0.0.1`).
- `python manage.py collectstatic` para publicar `STATIC_ROOT`
  (`staticfiles/`) detrás de un servidor web o un CDN.
- Una base de datos accesible con el rol `siglog` y las mismas credenciales
  en variables de entorno del servidor.

Servir el proyecto con `runserver` en producción no es seguro ni
eficiente: hace falta un servidor WSGI (Gunicorn, uWSGI) detrás de un proxy
inverso. Configurar ese servidor y el resto de la infraestructura de
despliegue (contenedores, balanceo, TLS) queda **fuera del alcance de este
proyecto** (ver `docs/superpowers/specs/2026-08-16-sig-log-design.md`, §2.1).

**Sobre `SECRET_KEY` y `DEBUG` por defecto.** `config/settings.py` define
`SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-development-key")` y
`DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"`: si las variables de
entorno correspondientes no están presentes, el proyecto arranca con una
clave de desarrollo fija (no secreta) y con `DEBUG` activado. Esto es
intencional para que `git clone` + `pip install` + `migrate` funcione sin
configuración adicional en un entorno de evaluación académica, pero es
exactamente lo opuesto de lo que se necesita en cualquier despliegue real:
antes de exponer el proyecto fuera de `localhost`, hay que definir
`DJANGO_SECRET_KEY` (un valor generado, no el de ejemplo) y
`DJANGO_DEBUG=False` explícitamente en el entorno del servidor — de lo
contrario, el valor por defecto queda activo en silencio.
