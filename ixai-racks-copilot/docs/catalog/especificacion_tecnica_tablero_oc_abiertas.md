# Especificacion Tecnica

## Tablero de ordenes de compra abiertas

Stack objetivo: Streamlit + DuckDB + Text-to-SQL

Origen funcional:

- analisis de `data_produccion.xlsx`
- hoja `Tabla1`
- universo inicial reportado: 29 renglones, 16 POs abiertas de racks Golf/Variant VW

Audiencia:

- operacion para seguimiento diario
- direccion para revision semanal

Este documento funciona como instruccion de entrada para el crew de agentes y skills. Cada bloque indica responsabilidad por rol.

## 0. Narrativa que el tablero debe contar

Este tablero no debe limitarse a mostrar datos; debe comunicar riesgo y urgencia.

Hallazgos de negocio que el tablero debe exponer:

- avance real muy bajo en unidades frente al total
- valor pendiente dominante respecto al valor total
- partidas comprometidas para la semana en curso con avance casi nulo
- concentracion de riesgo en un planeador
- la columna `Condicion` no debe usarse como fuente de verdad del estado real de entrega

Principio rector:

- el dashboard debe priorizar exposicion, atraso y capacidad de accion
- las tablas son soporte; la historia principal debe ser visible en KPIs y graficas

## 1. Contrato de datos

Agente responsable:

- Data Engineer / ETL

Fuente:

- archivo `data_produccion.xlsx`
- hoja `Tabla1`

Reglas de ingestion obligatorias:

1. El Excel es un snapshot del estado actual, no un historico.
2. Si se requiere tendencia, el pipeline debe persistir snapshots propios con timestamp.
3. El ETL debe validar schema en cada carga.
4. Si cambia la estructura del archivo, la carga debe fallar con mensaje claro.

### Columnas esperadas

| Columna | Tipo esperado | Nota |
| --- | --- | --- |
| `Item` | int | folio de linea |
| `Costo Unitario` | float | MXN |
| `Total` | float | debe corresponder a `Costo Unitario × Qty.` |
| `Condicion` | string | valores tipo `Entregado VW` o `Pendiente`, no confiable para estatus real |
| `Peso` | float | hoy viene vacia; tratar como dato no disponible |
| `Dimensiones` | string | formato libre |
| `Cubicaje` | int | dato operativo |
| `RA` | string | referencia interna |
| `Lison` | string | referencia interna |
| `Ingeniero` | string | variable categorica |
| `Planeador` | string | variable categorica |
| `Description` | string | descripcion libre |
| `PO` | string o int | orden de compra |
| `PO Date` | date | fecha de la PO |
| `Qty.` | int | cantidad ordenada |
| `Entregados` | int | cantidad entregada |
| `Por Entregar` | int | esperado: `Qty. - Entregados` |
| `Fecha de Entrega` | string | formato `Semana NN`, sin anio |
| `%` | float | no confiar; recalcular |

### Riesgo principal del contrato de datos

`Fecha de Entrega` no trae anio. Eso vuelve ambigua una semana cuando coexisten datos de distintos ciclos anuales.

Decision de diseno obligatoria para ETL:

- derivar una fecha real usando `PO Date` y el numero de semana
- o asumir anio vigente y persistir explicitamente `semana_entrega_anio`
- la resolucion debe quedar materializada, no implícita en frontend

### Columnas derivadas obligatorias

Estas columnas deben calcularse en ETL, no en frontend:

- `avance_real_pct = Entregados / Qty.`
- `valor_pendiente = Costo Unitario * Por Entregar`
- `valor_entregado = Costo Unitario * Entregados`
- `estatus_real`
  - `Completo` si `Por Entregar = 0`
  - `Parcial` si `0 < Entregados < Qty.`
  - `Sin iniciar` si `Entregados = 0`
- `urgencia`
  - `Vencida`
  - `Semana actual`
  - `Proximas 2 semanas`
  - `Futura`

## 2. Arquitectura general

Arquitectura objetivo:

```text
data_produccion.xlsx
        |
        v
[ETL Agent] ingest.py
   - valida schema
   - calcula columnas derivadas
   - escribe a DuckDB
       * estado_actual
       * historico
        |
        v
DuckDB embebido
        |
        +--> App Streamlit
        |
        +--> Tab Text-to-SQL
```

Decisiones clave:

- usar DuckDB embebido, no servidor externo
- `estado_actual` se reemplaza en cada carga
- `historico` es append-only con `snapshot_ts`

Justificacion de DuckDB:

- embebido como SQLite, sin servidor
- mejor perfil analitico para agregaciones y ventanas
- integracion natural con pandas y Streamlit

## 3. Estructura funcional de la app Streamlit

Agente responsable:

- Frontend

Principios de navegacion:

- navegacion multipagina con `st.navigation` o patron equivalente
- filtros globales en sidebar
- los filtros deben aplicar a todas las tabs
- boton `Actualizar datos` visible en todas las vistas
- actualizar datos no debe requerir reinicio de la app

Filtros globales esperados:

- rango de semanas
- planeador
- ingeniero
- `estatus_real`

### Tabs objetivo

#### 1. Resumen ejecutivo

Audiencia primaria:

- direccion

Contenido esperado:

- KPIs principales
- avance global
- valor pendiente vs entregado
- top 5 riesgos por valor

#### 2. Operacion semanal

Audiencia primaria:

- operacion

Contenido esperado:

- piezas pendientes por semana de entrega
- semanas vencidas y semana actual resaltadas en rojo
- tabla accionable filtrable por PO y planeador

#### 3. Detalle por PO / Planeador

Audiencia primaria:

- operacion y direccion

Contenido esperado:

- drill-down por PO
- drill-down por planeador
- detalle de renglones
- `estatus_real` visible por registro

#### 4. Pregunta a tus datos

Audiencia primaria:

- operacion y direccion

Contenido esperado:

- chat Text-to-SQL
- transparencia de SQL generada
- resultado tabular y opcion grafica

## 4. Tab Pregunta a tus datos

Agente responsable:

- NL2SQL / Backend

### Flujo funcional

1. El usuario formula una pregunta en lenguaje natural.
2. El sistema construye un prompt con schema real de `estado_actual` y `historico`.
3. El modelo responde exclusivamente con una sentencia `SELECT`.
4. La sentencia se valida antes de ejecutar.
5. Se ejecuta en DuckDB en modo solo-lectura.
6. Se muestra la SQL generada junto con el resultado.
7. Se mantiene historial en `st.session_state`.

### Guardrails obligatorios

- solo permitir `SELECT`
- bloquear `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `PRAGMA`
- bloquear multiples statements
- forzar `LIMIT` si el usuario no lo especifica
- timeout de ejecucion
- conexion de solo-lectura

### Comportamiento esperado

- si la pregunta esta fuera del dominio de datos, responder que el asistente solo consulta ordenes de compra y no ejecutar SQL irrelevante
- si el resultado tiene estructura graficable simple, ofrecer visualizacion

### Casos de prueba minimos

- `Que POs tienen entregas vencidas?`
- `Cuanto valor pendiente tiene el ingeniero Adrian?`
- `Cual fue el avance hace dos semanas vs hoy?`
- `Dame las 5 partidas con mayor valor pendiente`

## 5. KPIs y visualizaciones

Agente responsable:

- Frontend

Condicion obligatoria:

- usar columnas derivadas del ETL
- no recalcular logica de negocio critica en el frontend

### KPIs principales

- `Avance global = SUM(Entregados) / SUM(Qty.)` sobre `estado_actual`
- `Valor pendiente total = SUM(valor_pendiente)`

### Visualizaciones obligatorias

- piezas pendientes por semana de entrega
  - tipo: bar chart
  - semanas vencidas y semana actual en rojo
  - resto en azul
- valor pendiente por planeador
  - tipo: barra horizontal
  - objetivo: detectar concentracion de riesgo
- distribucion de `estatus_real` por PO
  - tipo: stacked bar
  - categorias: `Completo`, `Parcial`, `Sin iniciar`
- tendencia de avance
  - tipo: linea
  - origen: tabla `historico`
  - condicion: visible solo si existen al menos 2 snapshots

## 6. Reglas de negocio y edge cases

Agente responsable:

- QA

Casos obligatorios:

- `Peso` vacio en todas las filas
  - el UI no debe mostrar `0` ni romper calculos dependientes
- `Condicion = Entregado VW` pero `Entregados = 0`
  - debe clasificar como `Sin iniciar` en `estatus_real`
- semanas ambiguas entre anios
  - no deben mezclarse en la misma grafica sin resolucion explicita
- columnas faltantes o renombradas en el Excel
  - el ETL debe fallar con mensaje claro
- pregunta fuera de alcance para Text-to-SQL
  - no debe inventar SQL sobre temas ajenos

## 7. Estructura de carpetas propuesta

```text
/app
  Home.py
  /pages
    1_Resumen_Ejecutivo.py
    2_Operacion_Semanal.py
    3_Detalle_PO_Planeador.py
    4_Pregunta_tus_Datos.py
  /etl
    ingest.py
    schema_contract.py
  /nl2sql
    prompt_builder.py
    guardrails.py
  /data
    raw/
    warehouse.duckdb
  requirements.txt
```

## 8. Checklist de entregables por agente

### Data Engineer

- `ingest.py`
- `schema_contract.py`
- validacion de columnas
- calculo de columnas derivadas
- tabla `historico` append-only funcionando

### Frontend

- 4 tabs de navegacion
- filtros globales en sidebar
- graficas con semana actual y vencidas resaltadas
- boton de actualizacion de datos sin reinicio

### NL2SQL

- guardrails de solo-lectura
- `LIMIT` forzado
- timeout de ejecucion
- prompt con schema real, no hardcodeado

### QA

- cobertura de edge cases de negocio
- validacion de estatus derivado
- validacion de ambiguedad temporal
- pruebas de preguntas dentro y fuera de alcance

## 9. Relacion con la documentacion del proyecto

Este documento debe leerse junto con:

- `../metricas_kpi.md`
- `dashboard_operativo.md`
- `glosario_columnas.md`
- `lineage_metricas.md`

## 10. Criterio de aceptacion

La implementacion cumple esta especificacion cuando:

- el ETL genera `estado_actual` e `historico`
- el estado real no depende de `Condicion`
- el tablero muestra riesgo y urgencia de forma visible
- las tabs separan correctamente vista ejecutiva y operativa
- el modulo Text-to-SQL opera con guardrails de lectura
- los casos borde definidos por QA pasan de forma consistente
