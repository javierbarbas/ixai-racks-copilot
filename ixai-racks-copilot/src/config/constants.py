"""
constants.py
============
Fuente única de verdad para colores, nombres de columnas y umbrales del proyecto.

Si el cliente cambia colores corporativos o el esquema del Excel cambia de nombre,
solo se edita este archivo — ningún otro módulo requiere cambios.
"""

# ---------------------------------------------------------------------------
# PALETA CORPORATIVA (Tailwind-inspired, dark theme)
# ---------------------------------------------------------------------------

class Colors:
    # Primarios (paleta ejecutiva sobria)
    NAVY         = "#16324F"
    STEEL        = "#2F4858"
    TEAL         = "#2E6F95"
    SKY          = "#4F7CAC"

    # Semánticos
    SUCCESS       = "#2E8B57"   # verde pino
    SUCCESS_LIGHT = "#34d399"
    WARNING       = "#C08A00"   # ámbar sobrio
    WARNING_LIGHT = "#fbbf24"
    DANGER        = "#B23A48"   # rojo ladrillo

    # Neutros
    BG_APP         = "#F7F8FA"
    BG_CARD        = "#FFFFFF"
    TEXT_PRIMARY   = "#1F2933"
    TEXT_SECONDARY = "#52606D"
    TEXT_MUTED     = "#7B8794"
    CARD_BG        = "#FFFFFF"
    CARD_BORDER    = "#D9E2EC"

    # Gradientes completos (usados en mark_bar de Altair)
    CHART_PALETTE = [NAVY, TEAL, SKY, SUCCESS, WARNING, DANGER]


# ---------------------------------------------------------------------------
# ESQUEMA DE COLUMNAS DEL EXCEL
# Cambiar aquí si el cliente renombra columnas en data/produccion_racks.xlsx
# ---------------------------------------------------------------------------

class Columns:
    RA               = "RA"
    QTY              = "Qty."
    ENTREGADOS       = "Entregados"
    POR_ENTREGAR     = "Por Entregar"
    TOTAL            = "Total"
    COSTO_UNITARIO   = "Costo Unitario"
    INGENIERO        = "Ingeniero"
    PLANEADOR        = "Planeador"
    CONDICION        = "Condición"          # puede venir también como "Condicion"
    CONDICION_ALT    = "Condicion"
    DESCRIPTION      = "Description"
    PO_DATE          = "PO Date"
    FECHA_ENTREGA    = "Fecha de Entrega"
    ITEM             = "Item"
    PO               = "PO"

    # Columnas numéricas que deben castearse a float al cargar
    NUMERIC_COLS = [QTY, ENTREGADOS, POR_ENTREGAR, TOTAL, COSTO_UNITARIO]

    # Columnas de texto usadas como filtros en el sidebar
    FILTER_COLS = [INGENIERO, PLANEADOR]


# ---------------------------------------------------------------------------
# UMBRALES DE NEGOCIO
# ---------------------------------------------------------------------------

class Thresholds:
    # DER: Delivery Efficiency Rate
    DER_GOOD    = 85.0   # % — zona verde
    DER_WARNING = 60.0   # % — zona ámbar (por debajo → rojo)

    # Capital atorado como % del monto total → alerta si supera este valor
    CAPITAL_ATADO_WARNING_PCT = 40.0

    # OTD (On-Time Delivery)
    OTD_TARGET  = 95.0
    OTD_WARNING = 90.0

    # Variación aceptable de Lead Time vs baseline (% incremento)
    LEAD_TIME_WARNING_PCT = 15.0

    # Ventana de riesgo financiero (días hacia adelante)
    RISK_LOOKAHEAD_DAYS = 7


# ---------------------------------------------------------------------------
# TEXTOS DE LA UI (internacionalización futura)
# ---------------------------------------------------------------------------

class Labels:
    APP_TITLE    = "IxAI Racks Copilot"
    APP_SUBTITLE = "Panel Analítico On-Premise & Copiloto Inteligente para el Seguimiento de Producción y Órdenes"

    KPI_OTD         = "OTD"
    KPI_LEAD_TIME   = "Lead Time Promedio"
    KPI_BACKLOG     = "Backlog en Riesgo"

    KPI_FOOT_OTD       = "Objetivo >= 95%"
    KPI_FOOT_LEAD_TIME = "Dias PO -> Entrega"
    KPI_FOOT_BACKLOG   = "Pendiente vencido o <= 7 dias"
