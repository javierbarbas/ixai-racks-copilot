# Lineage de Metricas

Este documento mapea cada indicador visible a sus columnas fuente, reglas y funciones de implementacion.

## Estado Global

- Funcion: `compute_kpis`
- Depende de: `otd_status`, `lead_time_status`, `backlog_status`
- Columnas fuente indirectas:
  - `Condicion`
  - `Fecha de Entrega`
  - `PO Date`
  - `Total`

## OTD

- Funcion: `compute_kpis`
- Columnas fuente:
  - `Fecha de Entrega`
  - `Condicion`
  - fallback: `Entregados`, `Qty.`
- Reglas:
  - solo ordenes vencidas al corte
  - entregada si `Condicion` contiene `entregado`

## Lead Time Promedio

- Funcion: `compute_kpis`
- Columnas fuente:
  - `PO Date`
  - `Fecha de Entrega`
- Regla:
  - se excluyen diferencias negativas y valores nulos

## Backlog en Riesgo

- Funcion: `compute_kpis`
- Columnas fuente:
  - `Fecha de Entrega`
  - `Condicion`
  - `Total`
- Regla:
  - ventana de 7 dias hacia adelante

## Proporcion de Carga

- Funcion: `render_operational_insights`
- Columnas fuente:
  - `PO`
  - `Por Entregar`
- Regla:
  - se calcula preferentemente por PO agrupada

## Linea de Tiempo

- Funcion: `render_operational_insights`
- Columnas fuente:
  - `Fecha de Entrega`
  - fallback: `Fecha_Entrega_Normalizada`
- Regla:
  - clasifica cada orden como `Forecast` o `Atrasado`
  - agrupa por semana inicio

## Riesgo por Planeador

- Funcion: `risk_by_owner`
- Columnas fuente:
  - `Planeador`
  - `Fecha de Entrega`
  - `Condicion`
  - `Total`
  - `Por Entregar` o `Qty.`

## Alertas Criticas

- Funcion: `prioritized_actions`
- Columnas fuente:
  - `PO`
  - `Item`
  - `RA`
  - `Description`
  - `Planeador`
  - `Ingeniero`
  - `Fecha de Entrega`
  - `Por Entregar`
  - `Total`
- Regla:
  - solo ordenes no entregadas
  - se prioriza por fecha, atraso y monto

## Punto de entrada de la vista

- Archivo: `main.py`
- Flujo:
  - `load_data_bundle()`
  - `render_kpi_cards(df)`
  - `render_operational_insights(df)`
  - `render_alerts_table(df)`