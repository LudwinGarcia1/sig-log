# SIG-LOG — Sistema Integral de Gestión Logística

SIG-LOG administra vehículos, operadores, clientes, rutas, entregas,
combustible y mantenimiento de una flotilla de transporte, y responde con
datos las diez preguntas del caso de estudio: qué rutas se usan más, qué
vehículos cuestan más, qué operadores entregan más, dónde se concentran los
retrasos, qué vehículos consumen más combustible, cuáles son las causas de
retraso, qué unidades necesitan servicio, si una entrega llegará tarde, si
existen grupos de rutas similares y cuáles son los horarios de mayor
saturación. Las respuestas viven en un data warehouse dimensional poblado por
un proceso ETL propio y en dos modelos de minería de datos entrenados sobre
ese almacén.

| | |
|---|---|
| **Proyecto** | SIG-LOG — Sistema Integral de Gestión Logística |
| **Asignatura** | Extracción del conocimiento en bases de datos (9° cuatrimestre) |
| **Programa** | Ingeniería en Desarrollo y Gestión de Software |
| **Autor** | Ludwin García |

## Requisitos

| Componente | Versión verificada |
|---|---|
| Python | 3.13.14 |
| PostgreSQL | 18 |
| git | 2.52.0 |
| Django | 5.2.17 (instalado vía `requirements.txt`) |

## Instalación en cinco pasos

```powershell
git clone <url> SIG_LOG; cd SIG_LOG
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env       # y edita DB_PASSWORD
```

El proyecto se conecta a PostgreSQL como un rol dedicado (`siglog`), nunca como
`postgres`. Créalo antes de migrar (usando `psql -U postgres` u otra herramienta
administrativa, no `createdb`, porque el rol y la base los crea el bloque SQL
de abajo, no el usuario `postgres`):

```sql
CREATE ROLE siglog LOGIN PASSWORD '...' CREATEDB;
CREATE DATABASE siglog OWNER siglog;
```

Detalle completo de la instalación de PostgreSQL en Windows y la creación del
rol: [`docs/Manual_Tecnico.md`](docs/Manual_Tecnico.md#2-requisitos-e-instalación).

## Puesta en marcha

```powershell
python manage.py migrate
python manage.py loaddata delay_causes
python manage.py seed_demo --months 18 --seed 42
python manage.py run_etl --rebuild
python manage.py train_models
python manage.py runserver
```

Con el servidor arriba, entra a `http://127.0.0.1:8000/`. El orden importa:
`migrate` crea los esquemas `public`, `staging` y `dw`; `loaddata` carga el
catálogo de causas de retraso que `seed_demo` exige encontrar; `seed_demo`
genera 18 meses de operación sintética con semilla fija (reproducible);
`run_etl --rebuild` puebla el almacén desde cero; `train_models` entrena los
cuatro modelos de minería y genera sus figuras de diagnóstico.

**Advertencia:** `python manage.py test` vuelve a entrenar los modelos con los
datos de prueba y sobrescribe `ml/artifacts/` y `static/ml/`. Si corriste las
pruebas después de `train_models`, repite `python manage.py train_models`
antes de usar el dashboard. Detalle en
[`docs/Manual_Tecnico.md`](docs/Manual_Tecnico.md#10-mantenimiento-y-solución-de-problemas).

## Estructura del repositorio

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
│   ├── core/               BaseModel, CrudConfig, navegación, plantillas base
│   ├── customers/          M1  Clientes
│   ├── vehicles/           M2  Vehículos
│   ├── operators/          M3  Operadores
│   ├── routes/             M4  Rutas
│   ├── deliveries/         M5  Entregas
│   ├── fuel/                M6  Combustible
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

## Los ocho módulos

| Módulo | URL | Propósito |
|---|---|---|
| M1 Clientes | `/clientes/` | Alta, edición y baja de las empresas que reciben entregas. |
| M2 Vehículos | `/vehiculos/` | Inventario de la flotilla, odómetro y estatus operativo. |
| M3 Operadores | `/operadores/` | Choferes, licencias y antigüedad. |
| M4 Rutas | `/rutas/` | Corredores origen-destino, distancia y zona. |
| M5 Entregas | `/entregas/` | Programación, cierre de llegada y captura de retrasos. |
| M6 Combustible | `/combustible/` | Registro de cargas de combustible y rendimiento. |
| M7 Mantenimiento | `/mantenimiento/` | Órdenes de taller, preventivas y correctivas. |
| M8 Reportes y análisis | `/reportes/` | Dashboard, costos, alertas, predicción y conglomerados. |

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/Manual_Usuario.md`](docs/Manual_Usuario.md) | Guía de uso, capítulo por módulo, con capturas. |
| [`docs/Manual_Tecnico.md`](docs/Manual_Tecnico.md) | Instalación, configuración, ETL, minería, pruebas, despliegue. |
| [`docs/Arquitectura.md`](docs/Arquitectura.md) | Capas, esquemas, diagramas y decisiones de diseño. |
| [`docs/Diccionario_Datos.md`](docs/Diccionario_Datos.md) | Cada tabla y columna, en los tres esquemas. |
| [`docs/U1_Analisis_Metodologia.md`](docs/U1_Analisis_Metodologia.md) | Comparativo IA/ML/DM/Big Data y metodología CRISP-DM. |
| [`docs/U2_Data_Warehouse.md`](docs/U2_Data_Warehouse.md) | Esquema estrella, fuentes, limpieza y parámetros del ETL. |
| [`docs/U3_Analisis_Supervisado.md`](docs/U3_Analisis_Supervisado.md) | Clasificación y regresión de retrasos. |
| [`docs/U4_Analisis_No_Supervisado.md`](docs/U4_Analisis_No_Supervisado.md) | PCA y K-means sobre el perfil de rutas. |
| [`docs/U5_Visualizacion.md`](docs/U5_Visualizacion.md) | Gráficas del dashboard y respuesta a las diez preguntas. |

## Pruebas

```powershell
python manage.py test
```

La suite corre 189 pruebas: reglas de negocio de cada módulo, las ocho técnicas
de limpieza del ETL con caso válido e inválido, el proceso ETL de extremo a
extremo, la ausencia de fuga de datos en las matrices de minería y el
entrenamiento completo de los cuatro modelos. Recuerda re-entrenar los modelos
después de correr la suite (ver advertencia arriba).
