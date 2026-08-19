# Manual de Usuario — SIG-LOG

## 1. Introducción

SIG-LOG es el sistema de información de una empresa de transporte y
distribución de mercancías. Reemplaza los archivos y sistemas dispersos con un
único lugar donde capturar clientes, vehículos, operadores, rutas, entregas,
combustible y mantenimiento, y donde consultar en qué está fallando la
operación: rutas más usadas, vehículos más costosos, causas de retraso,
unidades que necesitan servicio, y si conviene predecir el retraso de una
entrega antes de que ocurra.

Lo usa una sola persona con perfil administrador (no hay roles ni permisos
granulares — ver `docs/Arquitectura.md`). Este manual está escrito para quien
nunca ha visto el sistema.

## 2. Cómo ingresar

Con el servidor corriendo (`python manage.py runserver`), abre
`http://127.0.0.1:8000/` en el navegador. El sistema pide sesión, así que lo
primero que verás es la pantalla de acceso:

![Acceso](img/01_acceso.jpg)

Escribe el usuario y la contraseña que creó quien instaló el sistema con
`python manage.py createsuperuser` y presiona **Entrar**. Si tecleas mal algo,
la misma pantalla lo avisa y te deja intentar de nuevo.

Ya dentro, la barra superior lista los ocho módulos; el resaltado en negritas
("Reportes") es el módulo de análisis. A la derecha aparece tu nombre de
usuario y el botón **Salir**, que cierra la sesión y te regresa a la pantalla
de acceso.

![Inicio](img/02_inicio.jpg)

Si todavía no has iniciado sesión y escribes directo una dirección como
`/reportes/costos/`, el sistema te manda primero al acceso y, en cuanto
entras, te deposita en esa misma pantalla.

## 3. Capítulo por módulo

Los siete módulos de captura comparten el mismo patrón: una lista con
buscador y paginación, un botón "Nuevo" y, por fila, "Editar" y "Baja". Nada
de esto se explica dos veces por módulo; solo las reglas propias de cada uno.

### 3.1 Clientes

Registra las empresas que reciben entregas. El buscador filtra por código,
razón social o RFC.

**Registrar un cliente**: código único (`CLI-0001`, se guarda en mayúsculas),
razón social, RFC (se guarda en mayúsculas), contacto, teléfono, correo
(opcional), dirección, ciudad, estado, código postal y tipo de cliente
(Premium, Regular u Ocasional). Ningún campo tiene validación cruzada más
allá de estas normalizaciones.

**Dar de baja** no borra el registro: pone `is_active` en falso. El cliente
desaparece de la lista y de los selectores de nuevas entregas, pero sus
entregas históricas permanecen intactas para la auditoría y para el ETL.

![Lista de clientes](img/03_clientes_lista.jpg)

### 3.2 Vehículos

Inventario de la flotilla. El buscador filtra por placa, número económico,
marca o modelo.

**Registrar un vehículo**: placa (única; se guarda en mayúsculas sin guiones
ni espacios), número económico (único), marca, modelo, año (debe estar entre
1980 y el año siguiente al actual), tipo (Camión, Camioneta, Tráiler,
Pick-up), capacidad de carga, tipo de combustible, capacidad de tanque,
odómetro actual, fecha de adquisición, kilometraje del próximo servicio,
fecha del último servicio y estatus (Disponible, En ruta, En mantenimiento,
Fuera de servicio).

**Dar de baja** desactiva el vehículo; deja de aparecer como opción al
capturar una entrega, una carga de combustible o un mantenimiento nuevos.

![Lista de vehículos](img/04_vehiculos_lista.jpg)

### 3.3 Operadores

Choferes asignados a las entregas. El buscador filtra por número de empleado,
nombre o número de licencia.

**Registrar un operador**: número de empleado (único), nombre, apellidos,
número de licencia, tipo de licencia (A, B, C o E — federal), vigencia de la
licencia, fecha de ingreso, teléfono y estatus (Activo, Vacaciones,
Inactivo). El formulario rechaza una vigencia de licencia anterior a la
fecha de ingreso.

![Lista de operadores](img/05_operadores_lista.jpg)

### 3.4 Rutas

Corredores fijos origen-destino que la flotilla atiende.

**Registrar una ruta**: código único (`RUT-001`), nombre, ciudad de origen y
destino, distancia en kilómetros (debe ser mayor que cero), duración estimada
en minutos, tipo de ruta (Local, Regional, Foránea), zona y costo de
casetas.

El tipo de ruta que elijas aquí es el que agrupa la demanda por servicio en el
reporte de Operación (sección 5.2).

![Lista de rutas](img/06_rutas_lista.jpg)

### 3.5 Entregas

El módulo central: cada fila es un envío de un cliente por una ruta, con un
vehículo y un operador asignados. El buscador filtra por folio, cliente,
código de ruta o placa.

**Registrar una entrega**: folio único, cliente, ruta, vehículo, operador,
salida programada, llegada programada (debe ser posterior a la salida
programada), peso de carga (no puede exceder la capacidad del vehículo
elegido), número de bultos, valor declarado, flete y estatus. La salida y
llegada reales, y la causa de retraso, normalmente no se capturan aquí sino
al cerrar la entrega (sección 4).

![Lista de entregas](img/07_entregas_lista.jpg)

### 3.6 Combustible

Registro de cada carga de combustible. El buscador no está disponible para
capturas de pantalla adicionales, pero el patrón de búsqueda es el mismo.

**Registrar una carga**: folio único, vehículo, operador, entrega asociada
(opcional), fecha y hora, estación, litros (mayor que cero, y el sistema
rechaza una carga que supere el doble de la capacidad del tanque del
vehículo — probablemente un error de captura), precio por litro y odómetro
(no puede ser negativo). El costo total se calcula solo.

![Lista de combustible](img/08_combustible_lista.jpg)

### 3.7 Mantenimiento

Órdenes de taller contra un vehículo.

**Registrar un mantenimiento**: folio único, vehículo, tipo (Preventivo o
Correctivo), fecha de servicio, odómetro, descripción, taller, mano de obra,
refacciones (ninguno de los dos costos puede ser negativo), próximo
kilometraje de servicio, días fuera de servicio y estatus (Programado, En
proceso, Completado). El costo total se calcula solo.

Al completar una orden desde el botón correspondiente, el sistema actualiza
también el vehículo: su odómetro, su próximo kilometraje de servicio, la
fecha de su último servicio y su estatus vuelven a "Disponible".

![Lista de mantenimiento](img/09_mantenimiento_lista.jpg)

## 4. Registrar la llegada de una entrega

Desde la lista de Entregas, la acción de llegada abre un formulario con dos
campos: la fecha y hora reales de llegada, y la causa de retraso (solo
aplica si hubo retraso).

**Regla que hay que conocer:** un retraso de **más de 15 minutos** exige una
causa. Si la llegada excede la tolerancia y no se elige causa, el sistema
rechaza el cierre con un mensaje explícito. Una entrega exactamente 15
minutos tarde **no** se considera retrasada y no pide causa.

Al cerrar la entrega, el sistema calcula el retraso, marca el estatus
(Entregada o Entregada con retraso) y, si el vehículo estaba "En ruta", lo
regresa a "Disponible" automáticamente.

## 5. Reportes y análisis

Cinco pantallas, todas bajo "Reportes" en la barra de navegación. Cada una
explica cómo leerla, no solo qué contiene.

### 5.1 Panel general

![Panel general](img/10_panel_general.jpg)

Ocho tarjetas con los indicadores del periodo: entregas cerradas,
cumplimiento (porcentaje dentro de la tolerancia de 15 minutos), retraso
promedio, kilómetros recorridos, ingreso por flete, rendimiento medio de
combustible, y los dos costos (combustible y mantenimiento). Debajo, una
línea muestra la tendencia mensual de entregas y entregas con retraso, y una
dona reparte el gasto entre combustible y mantenimiento.

### 5.2 Operación

![Operación](img/11_operacion.jpg)

- **Demanda por tipo de servicio**: la dona reparte los envíos entre Local,
  Regional y Foránea. En la tabla de abajo, el renglón resaltado es el
  servicio con mayor demanda; junto a cada uno verás su participación sobre
  el total y su tasa de retraso.
- **Clientes con mayor demanda**: los diez clientes con más envíos, con la
  ciudad, el tipo de cliente y el flete que aportan.
- **Rutas más utilizadas** y **operadores con más entregas**: barras
  ordenadas de mayor a menor, con su tabla al lado.
- **Rutas con mayores retrasos**: solo considera rutas con al menos 20
  envíos, para que el promedio no lo distorsione una ruta con dos entregas.
- **Saturación por día y hora**: un mapa de calor. Entre más oscura la
  celda, más salidas hubo en esa combinación de día y hora; las columnas más
  oscuras son las horas saturadas de la operación.
- **Causas de retraso (Pareto)**: las barras son el conteo de entregas por
  causa; la línea es el porcentaje acumulado. Las causas a la izquierda del
  80% son las prioritarias — atacar esas primero reduce la mayoría de los
  retrasos con el menor número de acciones.

Los seis botones de la parte superior descargan cualquiera de estos cuadros
en CSV o Excel, incluidos los dos de demanda.

### 5.3 Costos

![Costos](img/12_costos.jpg)

- **Costo total por vehículo**: barras apiladas de combustible y
  mantenimiento por unidad. El combustible pesa más que el mantenimiento en
  casi todos los casos — el detalle está en `docs/U5_Visualizacion.md`.
- **Rendimiento por vehículo**: peor rendimiento primero, para ubicar de un
  vistazo qué unidades consumen más de lo esperado para su tipo.
- **Costo por kilómetro por ruta**: útil para negociar el flete de una ruta
  contra lo que realmente cuesta operarla.

### 5.4 Alertas de mantenimiento

![Alertas de mantenimiento](img/13_alertas_mantenimiento.jpg)

Esta pantalla no lee el almacén de datos: lee directamente los vehículos
activos, porque "¿qué vehículo necesita servicio hoy?" es una pregunta del
momento, no una que deba esperar a la siguiente corrida del ETL. Un vehículo
aparece en **severidad alta** si ya rebasó su kilometraje de servicio, si
nunca ha tenido un servicio registrado, o si pasaron más de 180 días desde el
último; aparece en **severidad media** si le faltan 1,000 km o menos para el
siguiente servicio.

### 5.5 Predicción de retraso

![Predicción](img/14_prediccion.jpg)

El formulario pide únicamente datos conocidos **antes** de que la entrega
salga: ruta, hora y día de salida, peso, bultos, tipo de vehículo y su
antigüedad, antigüedad del operador y tipo de cliente. Al calcular, el
sistema muestra la probabilidad de retraso y los minutos de retraso
esperados.

**La probabilidad es una estimación, no una certeza.** El modelo aprendió
patrones de 18 meses de operación histórica; una probabilidad de 0.70 quiere
decir que, entre entregas con características similares, siete de cada diez
llegaron tarde — no que esta entrega en particular vaya a llegar tarde con
certeza.

La misma pantalla muestra cómo se comportó el modelo en las pruebas: la
tabla de métricas de los dos algoritmos comparados, la matriz de confusión,
el gráfico de residuales de la regresión y las variables más influyentes.

### 5.6 Conglomerados de rutas

![Conglomerados](img/15_conglomerados.jpg)

El plano muestra cada ruta como un punto, coloreado según el grupo al que
pertenece. Los ejes son los dos componentes principales — combinaciones de
las variables originales (distancia, duración, tasa de retraso, envíos por
mes, costo por km, etc.) elegidas para que puntos cercanos en el plano
correspondan a rutas con comportamiento parecido. La tabla debajo del plano
resume cada grupo con su nombre en español:

- **Rutas urbanas congestionadas**: cortas, muy frecuentes, con la tasa de
  retraso más alta. Son candidatas a revisar horarios de salida o asignar
  vehículos más jóvenes.
- **Rutas foráneas eficientes**: largas, poco frecuentes, con la tasa de
  retraso más baja. No requieren intervención.
- **Rutas regionales estables**: comportamiento intermedio en todo.

## 6. Exportar reportes

Los botones "CSV" y "Excel" sobre cada tabla de Operación y Costos generan el
archivo con las mismas columnas que se ven en pantalla, en español, listo
para abrir en Excel o para adjuntar a un correo.

## 7. Preguntas frecuentes

**El dashboard aparece vacío.** El almacén de datos (`dw`) todavía no tiene
información. Ejecuta `python manage.py run_etl --rebuild` (requiere haber
corrido antes `seed_demo` o tener datos operativos capturados).

**La pantalla de predicción o de conglomerados dice que el modelo no está
entrenado.** Ejecuta `python manage.py train_models`.

**Un vehículo, operador o ruta que sé que existe no aparece en los
selectores.** Fue dado de baja (`is_active = False`). Sigue existiendo para
las entregas antiguas que lo referencian, pero ya no se ofrece para
capturas nuevas.

**No puedo eliminar una entrega, ni un cliente, vehículo, ruta u operador
referenciado por una entrega.** Las llaves foráneas de `Delivery` usan
`PROTECT`: la base de datos rechaza el borrado mientras exista al menos una
entrega que dependa de ese registro. Es la misma razón por la que "dar de
baja" desactiva en vez de borrar — ver `docs/Arquitectura.md`.

**Olvidé mi contraseña o no tengo usuario.** El sistema no tiene
recuperación por correo. Pide a quien administra el servidor que ejecute
`python manage.py createsuperuser` para darte un usuario nuevo, o
`python manage.py changepassword <usuario>` para reasignar el tuyo.

**Me sacó del sistema y no había presionado "Salir".** La sesión dura dos
semanas desde el último ingreso: es el valor por omisión de Django, y las
sesiones se guardan en la base de datos, así que sobreviven a un reinicio
del servidor. Vuelve a entrar con las mismas credenciales; no se pierde nada
de lo que hayas guardado.
