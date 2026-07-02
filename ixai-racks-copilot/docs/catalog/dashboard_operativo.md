# Dashboard Operativo

Este documento explica la estructura funcional de la pantalla principal `Control Operativo`.

## Vista general

La pantalla se divide en tres zonas:

1. KPIs superiores.
2. Zona media de insights operativos.
3. Tabla inferior de alertas criticas.

## 1. KPIs superiores

Render: `render_kpi_cards`

Bloques visibles:

- Estado Global
- OTD
- Lead Time Promedio
- Backlog en Riesgo

Objetivo:

- entregar una lectura ejecutiva inmediata del estado del proceso
- concentrar cumplimiento, eficiencia temporal y exposicion economica

## 2. Zona media de insights operativos

Render: `render_operational_insights`

Layout actual:

- columna izquierda amplia
- columna derecha angosta con dos tarjetas apiladas

### 2.1 Linea de Tiempo de Entregas

Ubicacion: columna izquierda

Muestra:

- ordenes por semana
- separacion entre `Forecast` y `Atrasado`
- linea vertical de `Hoy`

Uso:

- detectar concentraciones de carga futura
- visualizar atraso acumulado en el tiempo

### 2.2 Proporcion de Carga

Ubicacion: columna derecha superior

Muestra:

- porcentaje entregado
- porcentaje pendiente

Uso:

- medir composicion del universo actual de ordenes o POs

### 2.3 Backlog en Riesgo por Planeador

Ubicacion: columna derecha inferior

Muestra:

- responsables con mayor monto en riesgo
- comparacion horizontal del impacto economico

Uso:

- identificar focos de riesgo por responsable
- priorizar seguimiento operativo

## 3. Alertas Criticas

Render: `render_alerts_table`

Muestra:

- ordenes no entregadas
- fecha de entrega
- atraso
- riesgo financiero
- accion sugerida

Uso:

- operar el seguimiento diario
- enfocar al equipo en los casos mas urgentes

## Flujo de datos de la pantalla

1. `main.py` carga datos desde `load_data_bundle()`.
2. La vista `Control Operativo` invoca:
   - `render_kpi_cards(df)`
   - `render_operational_insights(df)`
   - `render_alerts_table(df)`
3. Cada bloque aplica su propia agregacion sobre el mismo dataframe base.

## Consideraciones de lectura

- un KPI puede estar en verde y aun asi existir alertas puntuales abajo
- el backlog financiero se interpreta mejor junto con la tabla de alertas
- el timeline muestra distribucion temporal, no monto
- el ranking por planeador muestra monto, no necesariamente cantidad de unidades

## Referencias cruzadas

- formulas: `../metricas_kpi.md`
- glosario: `glosario_columnas.md`
- trazabilidad: `lineage_metricas.md`