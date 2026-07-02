# Glosario de Columnas

Este documento resume las columnas de negocio mas relevantes usadas por el dashboard.

## Columnas operativas base

### RA

Identificador operativo asociado al registro. Se usa en tablas de seguimiento y alertas.

### Qty.

Cantidad solicitada. Alimenta volumen total, agregaciones por responsable y metricas base.

### Entregados

Cantidad ya entregada. Se usa para calcular volumen entregado y el fallback de OTD cuando no hay fecha de entrega.

### Por Entregar

Cantidad pendiente. Se usa para backlog, composicion entregado vs pendiente y carga pendiente por planeador.

### Total

Monto total economico del registro. Es la base del backlog financiero y del monto de riesgo en alertas.

### Costo Unitario

Costo por unidad. No es el driver principal de los KPIs visibles actuales, pero puede apoyar calculos derivados.

## Columnas de responsables

### Ingeniero

Responsable tecnico. Se usa en algunas visuales y tablas auxiliares.

### Planeador

Responsable de planeacion. Es clave para el ranking de backlog en riesgo por responsable.

## Columnas de estado y clasificacion

### Condicion

Texto que representa el estado de la orden. Si contiene la palabra `entregado`, la orden se considera entregada.

### Condicion Alt

Variante alternativa del nombre de columna de condicion cuando el origen no trae acento.

### Description

Descripcion del item o rack. Se usa para agregaciones descriptivas y tops de demanda.

## Columnas temporales

### PO Date

Fecha de emision o referencia de la PO. Se usa para calcular lead time.

### Fecha de Entrega

Fecha objetivo o comprometida de entrega. Se usa en OTD, timeline, backlog en riesgo y alertas.

### Fecha_Entrega_Normalizada

Campo normalizado derivado del pipeline cuando la fecha original llega en formatos heterogeneos. Sirve de respaldo para timeline y calculos temporales.

## Columnas de identificacion

### Item

Identificador de item o componente. Puede usarse para hotspots, descripciones y tablas accionables.

### PO

Identificador de orden de compra. Se usa para componer el indicador de proporcion de carga a nivel PO.

## Nota de gobierno

Los nombres oficiales de columnas y umbrales deben validarse siempre contra `src/config/constants.py`.