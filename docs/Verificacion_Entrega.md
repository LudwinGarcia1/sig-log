# Acta de verificación de entrega — SIG-LOG

**Fecha:** 16 de agosto de 2026
**Equipo:** Windows 11 · PostgreSQL 18.3 · Python 3.13.14 · Django 5.2.17
**Rama:** `feature/sig-log-implementation`

Este documento registra el resultado de verificar el sistema **desde una base de
datos destruida y recreada**, siguiendo únicamente los comandos del `README.md`.
No se aplicó ningún ajuste manual durante la secuencia.

---

## 1. Arranque desde base vacía

Se ejecutó `dropdb siglog` seguido de `createdb siglog`, dejando 0 tablas, y
después la secuencia documentada:

| Paso | Comando | Resultado | Tiempo |
|---|---|---|---|
| 1 | `python manage.py migrate` | OK | 8.3 s |
| 2 | `python manage.py loaddata delay_causes` | OK | 5.8 s |
| 3 | `python manage.py seed_demo --months 18 --seed 42` | OK | 14.2 s |
| 4 | `python manage.py run_etl --rebuild` | OK | 22.4 s |
| 5 | `python manage.py train_models` | OK | 28.8 s |

**Total: 79.7 segundos**, sin intervención manual.

Salida real del paso 3:

```
Sembrado completo: 120 clientes, 50 vehículos, 40 operadores, 60 rutas,
27218 entregas, 3644 cargas, 566 mantenimientos.
```

Salida real del paso 5:

```
Entrenando sobre 26886 entregas…
Clasificación · ganador: Regresión logística (F1 0.780, exactitud 0.753)
Regresión · MSE 802.69 · MAE 20.91 · R² 0.226
Agrupamiento · k=3 · silueta 0.738 · varianza explicada 88.7%
```

---

## 2. Criterios de éxito del documento de diseño

### Criterio 1 — la secuencia levanta el sistema desde cero

**Cumplido.** Ver sección 1.

### Criterio 2 — los ocho módulos permiten alta, consulta, edición y baja

**Cumplido.** Los siete módulos de captura se construyen sobre el motor CRUD
genérico de `apps/core/views.py`, cuyo comportamiento está cubierto por pruebas
(listado, búsqueda, alta, y baja lógica que conserva el registro). El octavo
módulo, Reportes y análisis, expone seis pantallas. Ver criterio 6.

### Criterio 3 — el data warehouse está poblado y con bitácora consultable

**Cumplido.**

| Tabla | Filas |
|---|---|
| `dw.dim_date` | 546 |
| `dw.dim_time` | 24 |
| `dw.dim_customer` | 120 |
| `dw.dim_vehicle` | 50 |
| `dw.dim_operator` | 40 |
| `dw.dim_route` | 60 |
| `dw.dim_delay_cause` | 8 |
| `dw.fact_delivery` | 26 886 |
| `dw.fact_fuel` | 3 624 |
| `dw.fact_maintenance` | 566 |

`dw.etl_log`: **26 filas, 0 con estatus distinto de SUCCESS**.
`dw.etl_error`: **352 registros en cuarentena**, cada uno con la regla que lo
rechazó y su carga original.

### Criterio 4 — el clasificador supera 0.75 de F1

**Cumplido: F1 = 0.7795** sobre 5 378 filas de prueba retenidas.

### Criterio 5 — el agrupamiento supera 0.40 de coeficiente de silueta

**Cumplido: silueta = 0.7381** con k = 3, casi el doble del umbral.

### Criterio 6 — las diez preguntas se responden desde el dashboard

**Cumplido.** Las catorce pantallas responden HTTP 200:

```
200 /                          200 /reportes/
200 /clientes/                 200 /reportes/operacion/
200 /vehiculos/                200 /reportes/costos/
200 /operadores/               200 /reportes/mantenimiento/
200 /rutas/                    200 /reportes/prediccion/
200 /entregas/                 200 /reportes/conglomerados/
200 /combustible/
200 /mantenimiento/
```

Exportaciones verificadas:

```
200  rutas.csv              4 283 bytes
200  costos-vehiculo.xlsx   7 474 bytes
```

El detalle de qué pantalla responde cada una de las diez preguntas está en
`docs/U5_Visualizacion.md`.

---

## 3. Suite de pruebas

```
Ran 201 tests in 270.178s

OK
```

**201 pruebas, todas en verde**, sobre los ocho módulos, el generador, el data
warehouse y los modelos de minería.

---

## 4. Advertencia sobre el orden de ejecución

`python manage.py test` **sobrescribe los modelos entrenados**.
`TrainModelsCommandTest` invoca `train_models`, y ese comando escribe en
`ml/artifacts/` y `static/ml/`, que son rutas del sistema de archivos y no de la
base de pruebas. El resultado es que la suite deja modelos entrenados sobre el
conjunto de prueba de 3 a 4 meses, y el dashboard muestra métricas peores que
las que citan los documentos.

**Remedio:** ejecutar `python manage.py train_models` después de cualquier
corrida de pruebas. Así se hizo al cerrar esta verificación, y `metrics.json`
quedó con 26 886 filas entrenadas y 5 378 de prueba.

Esto está documentado también en `docs/Manual_Tecnico.md`, sección de solución
de problemas.

**Actualización:** esta limitación quedó corregida posteriormente. Las
pruebas que entrenan modelos (`TrainModelsCommandTest`, `PredictionViewTest`
y `UntrainedModelTest`) ahora redirigen `ARTIFACT_DIR`, `CLASSIFIER_PATH`,
`REGRESSOR_PATH`, `CLUSTER_PATH`, `FIGURE_DIR` y `METRICS_PATH` a un
directorio temporal vía `unittest.mock.patch.object`, así que
`python manage.py test` ya no toca `ml/artifacts/` ni `static/ml/` y el
remedio manual descrito arriba deja de ser necesario.

---

## 5. Estado final

| | |
|---|---|
| Módulos obligatorios | 8 de 8 |
| Unidades temáticas cubiertas | 5 de 5 |
| Criterios de éxito del diseño | 6 de 6 |
| Pruebas automatizadas | 201, todas en verde |
| Arranque desde base vacía | 79.7 s, sin pasos manuales |

Verificado sobre la rama `feature/sig-log-implementation`.

**Este corte quedó superado por la sección 6**, que registra la verificación
del 18 de agosto tras cerrar los tres pendientes: 217 pruebas y control de
acceso en todas las pantallas.


---

## 6. Segunda verificación — 18 de agosto de 2026

Después del acta original se cerraron tres pendientes: el reporte de demanda
por tipo de servicio y por cliente, las capturas faltantes del manual de
usuario y el control de acceso. Esto es lo que se verificó sobre esos
cambios, en la rama `main`.

### 6.1 Lo que se ejecutó

| Comprobación | Resultado |
|---|---|
| `python manage.py check` | Sin incidencias (0 silenciadas) |
| `python manage.py test` | **217 pruebas, `OK`**, 367.9 s |
| Las 14 pantallas protegidas con sesión abierta | Las 14 responden 200 |
| Las 14 pantallas protegidas sin sesión | Las 14 responden 302 hacia `/entrar/?next=<ruta>`, sin excepciones |
| Las 4 exportaciones sin sesión | Las 4 responden 302 hacia `/entrar/` |
| `/entrar/` sin sesión | 200 — es la única ruta abierta |
| `demanda-servicio.csv` | 200 · encabezados en español · los 3 tipos de servicio |
| `demanda-cliente.xlsx` | 200 · 12,098 bytes de libro de Excel |
| `ml/artifacts/metrics.json` tras la suite | Intacto: 26,886 filas, F1 0.7795, silueta 0.7381 |

Las 217 pruebas son 16 más que las 201 del acta original: once de control de
acceso (`apps/core/tests/test_authentication.py`) y cinco de los reportes de
demanda.

El desglose por paquete del `Manual_Tecnico.md` no cuadraba con el total
(84+55+37+13 = 189, no 201); se corrigió con los conteos reales medidos con
`DiscoverRunner.build_suite`: `apps` 109, `warehouse` 57, `ml` 38, `seed` 13.

### 6.2 Demanda por tipo de servicio

Medido sobre las 26,886 entregas del almacén:

| Servicio | Envíos | Participación | % retraso | Flete |
|---|---:|---:|---:|---:|
| **LOCAL** | **17,395** | **64.7%** | 67.9% | $13,333,916 |
| REGIONAL | 8,014 | 29.8% | 11.4% | $27,637,188 |
| FORÁNEA | 1,477 | 5.5% | 9.3% | $18,323,160 |

### 6.3 Lo que no se volvió a ejecutar

**El arranque desde base vacía de la sección 1 no se repitió.** Habría
exigido destruir la base de datos de trabajo, que hoy contiene los modelos
entrenados sobre las 26,886 entregas. Ninguno de los tres cambios toca el
ETL, el generador ni el esquema del almacén: la única migración añadida es la
de `django.contrib.auth`, que ya corría desde el inicio porque la aplicación
siempre estuvo en `INSTALLED_APPS`. La secuencia documentada sí incorpora un
paso nuevo, `python manage.py createsuperuser`, sin el cual no se puede
entrar al sistema.
