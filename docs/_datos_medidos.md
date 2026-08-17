# Hoja de datos medidos — SIG-LOG

Generada automaticamente contra la base siglog. Todas las cifras provienen
de la corrida de referencia: seed_demo --months 18 --seed 42 + run_etl --rebuild.

## Volumen OLTP (esquema public)
```
clientes | 120
vehiculos | 50
operadores | 40
rutas | 60
entregas | 27218
cargas_combustible | 3644
mantenimientos | 566
causas_retraso | 8
```

## Data warehouse (esquema dw)
```
dim_date | 546
dim_time | 24
dim_customer | 120
dim_vehicle | 50
dim_operator | 40
dim_route | 60
dim_delay_cause | 8
fact_delivery | 26886
fact_fuel | 3624
fact_maintenance | 566
```

## Bitacora ETL de la ultima corrida (dw.etl_log)
```
   phase   |    table_name    | rows_read | rows_written | rows_rejected | status  
-----------+------------------+-----------+--------------+---------------+---------
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
(26 rows)

```

## Registros en cuarentena por regla (dw.etl_error)
```
 source_table  |         rule          | registros 
---------------+-----------------------+-----------
 stg_delivery  | dates_are_coherent    |       272
 stg_delivery  | open_delivery         |        52
 stg_fuel_load | is_efficiency_outlier |        10
 stg_fuel_load | is_positive           |        10
 stg_delivery  | is_non_negative       |         8
(5 rows)

```

## Tasas de retraso medidas


## Arquetipos de ruta sembrados


## Unidad III — resultados supervisados


## Unidad III — variables mas influyentes (top 15)


## Unidad IV — barrido de k


## Unidad IV — perfil de cada conglomerado


## Tasas de retraso medidas
```
global                  27158 entregas cerradas   tasa 0.4788
zonas congestionadas    17586 entregas            tasa 0.6792
resto de zonas           9572 entregas            tasa 0.1107
```

## Arquetipos de ruta sembrados
```
URBANA    24 rutas    12-  45 km  22-32 km/h  28-55 envios/mes  zonas: METROPOLITANA, ORIENTE
REGIONAL  22 rutas    90- 280 km  52-68 km/h  12-26 envios/mes  zonas: CENTRO, BAJIO, OCCIDENTE
FORANEA   14 rutas   420- 900 km  68-82 km/h   3- 9 envios/mes  zonas: NORTE, SUR, GOLFO
```

## Unidad III - resultados supervisados
```
filas: 26886   entrenamiento 21508 / prueba 5378
ganador: Regresión logística

algoritmo                exactitud precision   sensib.       F1  ROC-AUC  F1 (VC 5)
Regresión logística         0.7527    0.6786    0.9180   0.7804   0.7861     0.7797
Random Forest               0.7512    0.6783    0.9134   0.7785   0.7774     0.7789

matriz de confusion (filas = real, columnas = predicho): [[1685, 1119], [211, 2363]]
regresion lineal:  MSE 787.45   RMSE 28.06   MAE 20.93   R2 0.2239
```

## Unidad III - variables mas influyentes (top 15)
```
 1. cat__route_code_RUT-054                      0.7554
 2. cat__route_type_LOCAL                        0.6632
 3. cat__distance_range_CORTA                    0.6632
 4. cat__route_type_FORANEA                      0.5468
 5. cat__distance_range_LARGA                    0.5468
 6. cat__route_type_REGIONAL                     0.4869
 7. cat__distance_range_MEDIA                    0.4869
 8. cat__route_code_RUT-046                      0.4710
 9. cat__route_code_RUT-032                      0.4243
10. cat__route_code_RUT-037                      0.3952
11. cat__route_code_RUT-060                      0.3876
12. cat__route_code_RUT-048                      0.3620
13. cat__zone_METROPOLITANA                      0.3456
14. cat__route_code_RUT-057                      0.3425
15. cat__zone_ORIENTE                            0.3176
```

## Unidad IV - barrido de k (metodo del codo y silueta)
```
  k      inercia      silueta   Davies-Bouldin
  2       121.08       0.6594           0.5085
  3        31.55       0.7381           0.4034  <-- elegido
  4        16.67       0.7380           0.3698
  5        13.14       0.5883           0.6187
  6        10.13       0.5538           0.6099
  7         7.71       0.5426           0.6378
  8         6.07       0.5310           0.6440
  9         5.15       0.5377           0.6431
 10         4.42       0.5486           0.5389

varianza explicada: PC1 0.7094 + PC2 0.1779 = 0.8874
```

## Unidad IV - perfil de cada conglomerado
```
Rutas urbanas congestionadas     24 rutas | dist   28.0 km | dur  94.8 min | tasa retraso 0.679 | retraso medio  38.4 min | envios/mes  40.3 | costo/km  28.95
Rutas foráneas eficientes        14 rutas | dist  680.2 km | dur 524.2 min | tasa retraso 0.096 | retraso medio  21.2 min | envios/mes   5.9 | costo/km  18.87
Rutas regionales estables        22 rutas | dist  171.2 km | dur 172.2 min | tasa retraso 0.114 | retraso medio  11.3 min | envios/mes  20.2 | costo/km  20.61
```

## Costos por vehiculo — matiz importante para la interpretacion

Pregunta del caso de estudio: "Que vehiculos generan mayores costos?"

La respuesta tiene dos capas y conviene no confundirlas:

```
TOP 10 MAS COSTOSOS (18 meses) — los diez son TRAILER
  #1 EC-0003  9+   combustible 614,121  mantenimiento 208,886  total 823,007
  #2 EC-0027  9+   combustible 616,058  mantenimiento 205,425  total 821,483
  #3 EC-0035  4-8  combustible 647,044  mantenimiento 122,522  total 769,566
  ...
  4 de los 10 son vehiculos de 9+ anos
```

1. El **tipo de vehiculo** domina el costo total. Los trailers rinden 2.2 km/L
   contra 8.1 de una pick-up, y el combustible pesa entre 3 y 8 veces mas que
   el mantenimiento. Por eso el top 10 son diez trailers.

2. La **antiguedad** domina el costo de mantenimiento, y se ve al comparar la
   flota completa:

```
COSTO TOTAL MEDIO POR RANGO DE ANTIGUEDAD
  0-3    13 vehiculos    356,658
  4-8    21 vehiculos    432,814
  9+     16 vehiculos    497,556     <- crecimiento monotono
```

   Dentro del mismo tipo de vehiculo, un trailer de 9+ anos gasta 149,000 a
   209,000 en mantenimiento contra 69,000 a 123,000 de uno joven.

Conclusion accionable: para reducir el gasto de combustible hay que revisar la
asignacion de trailers a rutas; para reducir el gasto de mantenimiento hay que
revisar el plan de renovacion de la flota. Son dos decisiones distintas y el
dato las separa.
