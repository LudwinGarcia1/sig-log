# Unidad I — Introducción al análisis de datos y metodología

## 1. Cuadro comparativo: IA / Machine Learning / Data Mining / Big Data

| Disciplina | Características | Beneficios | Restricciones y retos | Casos de aplicación | Lenguajes y herramientas |
|---|---|---|---|---|---|
| **Inteligencia Artificial (IA)** | Disciplina general que busca que un sistema imite tareas que requieren razonamiento humano: percepción, planeación, lenguaje, decisión. Engloba a las otras tres. | Automatiza tareas cognitivas, escala decisiones que antes requerían un experto humano. | Requiere grandes volúmenes de conocimiento o datos de calidad; los modelos pueden ser opacos ("caja negra"); riesgo de sesgo si los datos de entrenamiento lo traen. | Asistentes conversacionales, visión por computadora, sistemas de recomendación, vehículos autónomos. | Python, C++, Prolog; frameworks como TensorFlow, PyTorch. |
| **Machine Learning (ML)** | Subconjunto de la IA: algoritmos que aprenden un patrón a partir de datos de ejemplo, en vez de que el patrón se programe a mano. Se divide en supervisado, no supervisado y por refuerzo. | No hace falta codificar reglas explícitas; el modelo mejora con más datos; generaliza a casos no vistos. | Necesita datos etiquetados (en el caso supervisado) y suficiente volumen; sobreajuste si el modelo memoriza en vez de generalizar; exige validar con datos que el modelo no vio en entrenamiento. | Clasificación de correo no deseado, predicción de demanda, diagnóstico asistido, y en este proyecto: predicción de retraso de entregas y regresión de minutos de retraso. | Python (scikit-learn, en este proyecto), R, MATLAB. |
| **Data Mining (Minería de datos)** | Proceso de descubrir patrones, relaciones y conocimiento no evidente en grandes volúmenes de datos históricos, combinando estadística, bases de datos y aprendizaje automático. Es el proceso; ML es una de sus herramientas. | Convierte datos operativos acumulados en conocimiento accionable; encuentra relaciones que nadie planteó de antemano como hipótesis. | Exige un proceso disciplinado de preparación de datos (limpieza, integración) que suele tomar más tiempo que el modelado mismo; el resultado solo vale si los datos de origen son confiables. | Segmentación de clientes, detección de fraude, canasta de mercado, y en este proyecto: agrupamiento de rutas por comportamiento operativo. | SQL, Python, R, herramientas como RapidMiner, Weka. |
| **Big Data** | Gestión y análisis de datos caracterizados por volumen, velocidad y variedad que exceden la capacidad de una base de datos relacional convencional. | Permite analizar información a una escala que antes era inviable; habilita análisis en tiempo casi real sobre flujos continuos. | Exige infraestructura distribuida (clusters, almacenamiento distribuido); mayor complejidad operativa y de gobierno de datos. | Análisis de clickstream, IoT industrial, redes sociales a escala global. | Hadoop, Spark, Kafka, bases NoSQL (MongoDB, Cassandra). |

Este proyecto opera en la intersección de Data Mining y Machine Learning sobre
un volumen que **no** requiere Big Data: 27,218 entregas y sus tablas
relacionadas caben cómodamente en PostgreSQL y se procesan en segundos con
pandas y scikit-learn (ver `docs/U2_Data_Warehouse.md`, sección 2).

## 2. Objetivo y alcance del caso de estudio

### 2.1 Contexto y problema

Una empresa de transporte y distribución de mercancías opera una flotilla
que realiza entregas diarias a distintos clientes y destinos. Hoy la
información de vehículos, operadores, clientes, rutas, entregas,
combustible y mantenimiento está dispersa en archivos y sistemas separados.
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

### 2.2 Objetivo

Diseñar e implementar un sistema de información que administre vehículos,
operadores, clientes, rutas, entregas, combustible y mantenimiento, y que
genere información útil para optimizar las operaciones logísticas y apoyar
la toma de decisiones. El sistema debe permitir identificar patrones de
demanda de servicios, servicio con mayor demanda, horarios de mayor
saturación, frecuencia y rutas con mayor número de envíos.

### 2.3 Alcance comprometido

Dentro del alcance: los ocho módulos obligatorios operativos, un data
warehouse dimensional poblado por un ETL de tres fases, cuatro modelos de
minería de datos (dos supervisados, dos no supervisados), un dashboard con
cinco vistas analíticas, y la documentación completa (manuales y un
documento por unidad).

Fuera del alcance: autenticación por roles y permisos granulares,
geolocalización en tiempo real, aplicación móvil, despliegue en la nube, y
un segundo agrupamiento sobre clientes (marcado como opcional).

## 3. Justificación de la metodología

Se eligió **CRISP-DM** (Cross-Industry Standard Process for Data Mining)
sobre KDD y SEMMA.

| Metodología | Qué propone | Por qué se descartó (o se eligió) aquí |
|---|---|---|
| **KDD** (Knowledge Discovery in Databases) | Un proceso académico de cinco a nueve pasos centrado en el descubrimiento de conocimiento: selección, preprocesamiento, transformación, minería, interpretación. | Es el marco teórico del que CRISP-DM deriva, pero no dice nada sobre la comprensión del negocio ni sobre el despliegue como fases explícitas y documentadas — y este proyecto necesita justificar ambas cosas por separado (el caso de estudio y el dashboard). |
| **SEMMA** (Sample, Explore, Modify, Model, Assess) | Un flujo técnico de cinco pasos, propuesto por SAS, centrado exclusivamente en la parte de modelado estadístico. | No cubre la comprensión del negocio ni el despliegue; asume que los datos de muestra ya existen. Aquí los datos no preexisten — hay que generarlos, cargarlos a un almacén y exponerlos en un dashboard — así que un marco que empieza en "Sample" deja fuera la mitad del proyecto. |
| **CRISP-DM** | Seis fases iterativas: comprensión del negocio, comprensión de los datos, preparación de los datos, modelado, evaluación, despliegue. | Es la única de las tres que exige explícitamente entender el problema de negocio antes de tocar datos, y termina en un despliegue verificable — que es exactamente la estructura de este proyecto: un caso de estudio con diez preguntas, un data warehouse, dos pares de modelos y un dashboard que los expone. |

### 3.1 Las seis fases de CRISP-DM mapeadas a este proyecto

| Fase de CRISP-DM | Qué significa aquí | Dónde vive en el repositorio |
|---|---|---|
| Comprensión del negocio | El problema de la flotilla dispersa y las diez preguntas del caso de estudio | Sección 2 de este documento; `docs/superpowers/specs/2026-08-16-sig-log-design.md`, §1–2 |
| Comprensión de los datos | Qué entidades existen, su volumen, sus fuentes y sus patrones sembrados | Sección 4 de este documento; `docs/U2_Data_Warehouse.md`, sección 2 |
| Preparación de los datos | Limpieza, deduplicación, derivación de variables, exclusión de fuga de datos | `warehouse/etl/`, `docs/U2_Data_Warehouse.md` |
| Modelado | Clasificación y regresión de retraso (Unidad III); PCA y K-means sobre rutas (Unidad IV) | `ml/supervised.py`, `ml/unsupervised.py`, `docs/U3_…`, `docs/U4_…` |
| Evaluación | Métricas contra los umbrales del proyecto (F1 ≥ 0.75, silueta ≥ 0.40) | `ml/artifacts/metrics.json`, `docs/U3_…` sección 3, `docs/U4_…` sección 3 |
| Despliegue | El dashboard de `apps/analytics`, que expone los diez hallazgos como reportes navegables | `apps/analytics/`, `docs/U5_Visualizacion.md` |

## 4. Planeación de las etapas de análisis

| Etapa | Actividad | Entregable | Dónde vive en el repositorio |
|---|---|---|---|
| 1. Esqueleto | Proyecto Django, conexión a PostgreSQL, `apps/core` con `BaseModel` y el motor CRUD genérico | Aplicación ejecutable mínima | `config/`, `apps/core/` |
| 2. Módulos de captura | Los siete modelos de negocio, formularios, vistas CRUD y el catálogo de causas de retraso | Ocho módulos operativos | `apps/customers`, `apps/vehicles`, `apps/operators`, `apps/routes`, `apps/deliveries`, `apps/fuel`, `apps/maintenance` |
| 3. Generador sintético | `seed_demo` con los patrones de retraso, eficiencia y archetype de ruta sembrados | 18 meses de operación reproducible (semilla fija) | `seed/` |
| 4. Data warehouse | Esquemas, dimensiones, hechos, bitácoras y las tres fases del ETL | Almacén poblado y auditable | `warehouse/` |
| 5. Minería de datos | Matrices de entrenamiento, modelos supervisados y no supervisados, figuras de diagnóstico | Cuatro modelos entrenados y evaluados | `ml/` |
| 6. Dashboard | Las seis vistas de `analytics` y las exportaciones a CSV/Excel | Respuesta a las diez preguntas desde la interfaz | `apps/analytics/` |
| 7. Documentación | Manuales y un documento por unidad temática | Este conjunto de documentos | `README.md`, `docs/` |

Cada etapa deja el sistema en un estado ejecutable y demostrable, de modo
que si el tiempo se agotara en cualquier punto, lo ya construido funciona de
principio a fin.
