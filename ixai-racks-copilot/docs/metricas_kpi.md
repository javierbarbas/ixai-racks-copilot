# Documentacion de Metricas y KPIs

Este documento consolida la definicion funcional y tecnica de los indicadores usados en el dashboard ejecutivo de IxAI Racks Copilot.

Objetivos del documento:

- dejar trazable la formula exacta de cada KPI
- aclarar que columnas alimentan cada indicador
- documentar los umbrales de negocio vigentes
- explicar como interpretar cada visual del dashboard

## 1. Alcance

Esta documentacion cubre:

- KPIs principales de la fila superior
- indicadores intermedios de la vista Control Operativo
- logica de priorizacion de Alertas Criticas
- reglas de normalizacion de fechas que afectan los calculos

No cubre:

- visuales exploratorias fuera de la pantalla principal
- respuestas del asistente inteligente
- reglas de negocio externas al codigo actual

## 2. Flujo general de calculo

El flujo real de calculo es el siguiente:

1. Se carga el dataset operativo y, si existe, el dataset de casos especiales.
2. Se normalizan columnas de fecha mediante `with_datetime_cols`.
3. Se calcula el estado de entrega usando la columna `Condicion`.
4. Se calculan KPIs agregados con `compute_kpis`.
5. Se generan visuales complementarias para timeline, proporcion y riesgo por planeador.
6. Se construye la tabla de alertas con `prioritized_actions`.

## 3. Normalizacion previa de fechas

Fuente tecnica: `with_datetime_cols` / `_with_datetime_cols`

Reglas aplicadas:

- `PO Date` se convierte a `datetime` cuando existe.
- `Fecha de Entrega` se convierte a `datetime` cuando existe.
- Si `Fecha de Entrega` viene en formato `Semana N`, se convierte al lunes ISO de esa semana.
- Si la semana de entrega es numericamente menor que la semana de la PO, se asume que la entrega corresponde al siguiente anio.
- Si el valor no puede interpretarse como fecha valida, queda como `NaT`.

Impacto de esta etapa:

- evita que el timeline quede vacio por formatos mixtos
- hace comparable la fecha de entrega contra la fecha actual
- afecta directamente OTD, lead time, backlog en riesgo y alertas

## 4. Regla base para detectar orden entregada

Fuente tecnica: `_is_delivered`

Una orden se considera entregada si la columna `Condicion` contiene la palabra `entregado`, ignorando mayusculas, minusculas y espacios periféricos.

Interpretacion:

- cualquier fila no marcada como entregada entra como pendiente para las metricas de backlog y alertas

## 5. KPI Estado Global

Fuente tecnica: `compute_kpis`

### Definicion

Es el semaforo agregado del tablero. No se calcula directamente desde columnas fuente, sino desde la combinacion de tres estados parciales:

- `otd_status`
- `lead_time_status`
- `backlog_status`

### Regla de clasificacion

- `Critico`: si al menos uno de los tres estados esta en `danger`
- `En Riesgo`: si no hay `danger`, pero al menos uno esta en `warning`
- `Estable`: si todos estan en `good`

### Lectura de negocio

- `Critico` significa que existe una desviacion relevante en cumplimiento, tiempo o capital comprometido.
- `En Riesgo` significa que el sistema aun no esta en falla severa, pero ya muestra tension operativa.
- `Estable` significa que no se detectan alertas relevantes bajo los umbrales actuales.

## 6. KPI OTD

Fuente tecnica: `compute_kpis`

### Definicion

OTD mide el porcentaje de ordenes vencidas al corte que ya fueron entregadas.

### Variables usadas

- `today` = fecha actual normalizada
- `due_now` = ordenes con `Fecha de Entrega <= today`
- `delivered_mask` = ordenes detectadas como entregadas

### Formula principal

`OTD (%) = (on_time_count / due_count) * 100`

Donde:

- `due_count` = cantidad de ordenes vencidas con fecha valida
- `on_time_count` = cantidad de esas ordenes vencidas que ya estan entregadas

### Fallback

Si el dataset no trae `Fecha de Entrega`, se usa:

`OTD (%) = (total_entregados / total_qty) * 100`

### Umbrales actuales

- `good`: OTD >= 95
- `warning`: OTD >= 90 y < 95
- `danger`: OTD < 90

### Ejemplo conceptual

Si hoy hay 20 ordenes ya vencidas y solo 15 estan marcadas como entregadas:

`OTD = (15 / 20) * 100 = 75%`

Eso clasifica como `danger`.

## 7. KPI Lead Time Promedio

Fuente tecnica: `compute_kpis`

### Definicion

Es el tiempo promedio en dias entre la PO y la fecha de entrega.

### Formula base por fila

`LeadTimeDias = Fecha de Entrega - PO Date`

### Reglas de limpieza

- se excluyen nulos
- se excluyen valores negativos

### Formula agregada

`LeadTimePromedio = promedio(LeadTimeDias)`

### Delta porcentual

El tablero no muestra solo el promedio; tambien muestra su variacion relativa contra una referencia interna.

Regla de baseline:

- si hay 4 o mas registros validos: `baseline = mediana(LeadTimeDias)`
- si hay menos de 4: `baseline = LeadTimePromedio`

Formula:

`LeadTimeDeltaPct = ((LeadTimePromedio - baseline) / baseline) * 100`

Si `baseline = 0`, el delta se fuerza a `0`.

### Umbrales actuales

- `good`: delta <= 0
- `warning`: 0 < delta <= 15
- `danger`: delta > 15

### Lectura de negocio

- delta negativo o cero: el tiempo promedio esta controlado o mejora frente a su referencia
- delta positivo: el tiempo promedio empeora frente a su referencia

## 8. KPI Backlog en Riesgo Financiero

Fuente tecnica: `compute_kpis`

### Definicion

Es el monto economico comprometido en ordenes no entregadas que ya vencieron o que venceran dentro de la ventana de riesgo.

### Variables usadas

- `lookahead = today + 7 dias`
- `backlog_mask = orden no entregada y Fecha de Entrega <= lookahead`

### Formulas

`BacklogRiesgoFinanciero = suma(Total) en backlog_mask`

`BacklogRiesgoOrdenes = conteo de filas en backlog_mask`

### Estado del backlog

Primero se calcula:

`risk_pct = (BacklogRiesgoFinanciero / monto_total) * 100`

Luego se clasifica:

- `danger`: risk_pct >= 40
- `warning`: risk_pct >= 20 y < 40
- `good`: resto de casos

### Lectura de negocio

No solo importa cuantas ordenes estan en riesgo, sino cuanto capital representan sobre el monto total observado.

## 9. Metricas base de volumen

Fuente tecnica: `compute_kpis`

Estas metricas son de soporte y alimentan los KPIs visibles:

- `total_qty = suma de Qty.`
- `total_entregados = suma de Entregados`
- `por_entregar = max(0, total_qty - total_entregados)`
- `monto_total = suma de Total`
- `record_count = numero de filas del dataframe despues de normalizacion`

## 10. Indicador Proporcion de Carga

Fuente tecnica: `render_operational_insights`

### Objetivo

Mostrar el porcentaje de carga entregada frente a la pendiente.

### Regla de calculo

Caso preferente cuando existe `PO`:

1. Se agrupa `Por Entregar` por `PO`.
2. Se etiqueta cada PO como:
   - `Pendiente` si `PendienteTotal > 0`
   - `Entregado` si `PendienteTotal <= 0`
3. Se cuentan POs entregadas y pendientes.

Caso alterno si no existe `PO`:

- se calcula el estado directamente por fila con la misma regla sobre `Por Entregar`

### Formulas

- `delivered_count = conteo de Entregado`
- `pending_count = conteo de Pendiente`
- `total_count = delivered_count + pending_count`
- `delivered_pct = (delivered_count / total_count) * 100`
- `pending_pct = (pending_count / total_count) * 100`

### Lectura de negocio

Este visual no muestra monto ni unidades; muestra composicion del universo de POs o registros en estado entregado vs pendiente.

## 11. Indicador Linea de Tiempo

Fuente tecnica: `render_operational_insights`

### Objetivo

Mostrar el volumen semanal de ordenes entre dos estados operativos:

- `Forecast`
- `Atrasado`

### Logica de clasificacion

- `Atrasado` si `fecha_entrega < today`
- `Forecast` si `fecha_entrega >= today`

### Agregacion temporal

- `SemanaInicio = fecha_entrega` truncada al inicio de semana con `W-MON`
- `Ordenes = conteo por (SemanaInicio, EstadoEntrega)`

### Lectura de negocio

- concentra visualmente donde se acumula demanda atrasada
- muestra como se distribuye la carga futura por semana
- permite ver si el riesgo se concentra en pocas semanas o esta disperso

## 12. Indicador Backlog en Riesgo por Planeador

Fuente tecnica: `risk_by_owner` y `render_operational_insights`

### Definicion

Rankea responsables por monto en riesgo dentro de la misma ventana operativa de backlog.

### Filtro base

`risk_mask = no entregada y Fecha de Entrega <= today + 7 dias`

### Agregacion por planeador

- `RiesgoFinanciero = suma(Total)`
- `Ordenes = conteo de ordenes`
- `CargaPendiente = suma(Por Entregar)` si existe; si no, `suma(Qty.)`

### Orden de salida

- descendente por `RiesgoFinanciero`

### Lectura de negocio

Ayuda a responder quien concentra la mayor exposicion financiera en la ventana inmediata.

## 13. Tabla Alertas Criticas

Fuente tecnica: `prioritized_actions` y `render_alerts_table`

### Universo considerado

Solo incluye ordenes no entregadas.

### Campos calculados

- `DiasAtraso = today - Entrega`
  - positivo: orden vencida
  - negativo: aun faltan dias para vencer
  - nulo: fecha ausente o invalida
- `MontoRiesgo = Total` o `0` si no existe la columna
- `AccionSugerida`:
  - `Completar fecha de entrega` si `DiasAtraso` es nulo
  - `Escalar hoy con planeador` si `DiasAtraso > 0`
  - `Confirmar fecha y capacidad` si `DiasAtraso <= 0`

### Priorizacion

1. `Entrega` ascendente, si existe
2. `DiasAtraso` descendente
3. `MontoRiesgo` descendente

### Lectura de negocio

La tabla no es solo descriptiva; es una cola de atencion diaria priorizada por cercania temporal, atraso y exposicion economica.

## 14. Umbrales y parametros de negocio vigentes

Fuente tecnica: `src/config/constants.py`

- `OTD_TARGET = 95`
- `OTD_WARNING = 90`
- `LEAD_TIME_WARNING_PCT = 15`
- `RISK_LOOKAHEAD_DAYS = 7`
- `CAPITAL_ATADO_WARNING_PCT = 40`

## 15. Supuestos y limitaciones

- la deteccion de entregado depende de texto en `Condicion`
- el backlog financiero depende de la columna `Total`
- el lead time depende de la coexistencia de `PO Date` y `Fecha de Entrega`
- si la calidad de fechas es baja, OTD, timeline y alertas pueden degradarse
- la proporcion de carga puede calcularse por `PO` o por fila, segun disponibilidad de la columna `PO`

## 16. Trazabilidad al codigo

Implementaciones principales:

- `src/logic/metrics.py`
  - `compute_kpis`
  - `trend_kpis`
  - `risk_by_owner`
  - `prioritized_actions`
  - `with_datetime_cols`

- `src/dashboard/ui_components.py`
  - `render_kpi_cards`
  - `render_operational_insights`
  - `render_alerts_table`

- `main.py`
  - orquestacion de la vista `Control Operativo`

## 17. Recomendacion de mantenimiento

Cuando cambie una regla de negocio, actualizar primero:

1. `src/config/constants.py` si cambia umbral o nombre de columna
2. `src/logic/metrics.py` si cambia formula
3. este documento para mantener trazabilidad funcional
