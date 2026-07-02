"""Capa de lógica de negocio y métricas ejecutivas."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from datetime import datetime
import pandas as pd

from src.config.constants import Columns, Thresholds


PO_DATE_COL = getattr(Columns, "PO_DATE", "PO Date")
FECHA_ENTREGA_COL = getattr(Columns, "FECHA_ENTREGA", "Fecha de Entrega")
ITEM_COL = getattr(Columns, "ITEM", "Item")
PO_COL = getattr(Columns, "PO", "PO")


# ---------------------------------------------------------------------------
# DTO de KPIs — estructura tipada para evitar "magic dicts"
# ---------------------------------------------------------------------------

@dataclass
class KPISnapshot:
    """Snapshot de indicadores clave calculados sobre un DataFrame filtrado."""

    total_qty: int = 0
    total_entregados: int = 0
    por_entregar: int = 0
    monto_total: float = 0.0

    otd: float = 0.0
    otd_due_count: int = 0
    otd_on_time_count: int = 0
    otd_target: float = Thresholds.OTD_TARGET
    otd_status: str = "good"

    lead_time_promedio_dias: float = 0.0
    lead_time_delta_pct: float = 0.0
    lead_time_status: str = "good"

    backlog_riesgo_financiero: float = 0.0
    backlog_riesgo_ordenes: int = 0
    backlog_status: str = "good"

    estado_global: str = "Estable"
    record_count: int = 0
    active_filters: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Función principal de métricas
# ---------------------------------------------------------------------------

def _with_datetime_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if PO_DATE_COL in out.columns:
        if not pd.api.types.is_datetime64_any_dtype(out[PO_DATE_COL]):
            out[PO_DATE_COL] = pd.to_datetime(out[PO_DATE_COL], errors="coerce")

    if FECHA_ENTREGA_COL in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[FECHA_ENTREGA_COL]):
            return out

        raw = out[FECHA_ENTREGA_COL].astype("string").str.strip()
        week_pattern = raw.str.contains(r"(?i)semana\s*\d{1,2}", na=False)

        # First pass: only parse rows that are not encoded as delivery week labels.
        entrega = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
        direct_date_mask = (~week_pattern) & raw.notna() & raw.ne("")
        if direct_date_mask.any():
            entrega.loc[direct_date_mask] = pd.to_datetime(
                raw.loc[direct_date_mask],
                errors="coerce",
                dayfirst=True,
            )

        # Second pass: values like "Semana 27" mapped to Monday of ISO week.
        week_match = raw.str.extract(r"(?i)semana\s*(\d{1,2})", expand=False)
        week_num = pd.to_numeric(week_match, errors="coerce")

        mask_missing = entrega.isna() & week_num.notna()
        if mask_missing.any():
            po_year = None
            po_week = None
            if PO_DATE_COL in out.columns:
                po_dt = pd.to_datetime(out[PO_DATE_COL], errors="coerce")
                po_year = po_dt.dt.year
                po_week = po_dt.dt.isocalendar().week.astype("Int64")

            fallback_year = datetime.now().year

            def _week_to_date(idx: int, w: float):
                week = int(w)
                year = int(po_year.iloc[idx]) if po_year is not None and pd.notna(po_year.iloc[idx]) else fallback_year
                if po_week is not None and pd.notna(po_week.iloc[idx]):
                    # If delivery week is numerically before PO week, assume next year.
                    if week < int(po_week.iloc[idx]):
                        year += 1
                if week < 1 or week > 53:
                    return pd.NaT
                try:
                    return pd.Timestamp.fromisocalendar(year, week, 1)
                except ValueError:
                    return pd.NaT

            entrega.loc[mask_missing] = [
                _week_to_date(i, w)
                for i, w in zip(out.index[mask_missing], week_num.loc[mask_missing])
            ]

        out[FECHA_ENTREGA_COL] = entrega

    return out


def with_datetime_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Public helper to normalize date columns consistently across the app."""
    return _with_datetime_cols(df)


def _is_delivered(df: pd.DataFrame) -> pd.Series:
    if Columns.CONDICION not in df.columns:
        return pd.Series(False, index=df.index)
    cond = df[Columns.CONDICION].astype(str).str.strip().str.lower()
    return cond.str.contains("entregado", na=False)


def compute_kpis(df: pd.DataFrame) -> KPISnapshot:
    """Calcula KPIs accionables de nivel ejecutivo."""
    if df.empty:
        return KPISnapshot()

    df = _with_datetime_cols(df)
    total_qty = int(df[Columns.QTY].sum()) if Columns.QTY in df.columns else 0
    total_entregados = int(df[Columns.ENTREGADOS].sum()) if Columns.ENTREGADOS in df.columns else 0
    por_entregar = max(0, total_qty - total_entregados)
    monto_total = float(df[Columns.TOTAL].sum()) if Columns.TOTAL in df.columns else 0.0

    today = pd.Timestamp.now().normalize()
    delivered_mask = _is_delivered(df)

    # OTD operativo: de lo que ya vencio, cuanto ya esta entregado.
    if FECHA_ENTREGA_COL in df.columns:
        due_now = df[FECHA_ENTREGA_COL].notna() & (df[FECHA_ENTREGA_COL] <= today)
        due_count = int(due_now.sum())
        on_time_count = int((due_now & delivered_mask).sum())
        otd = (on_time_count / due_count * 100.0) if due_count > 0 else 0.0
    else:
        due_count = int(total_qty > 0)
        on_time_count = total_entregados
        otd = (total_entregados / total_qty * 100.0) if total_qty > 0 else 0.0

    if otd >= Thresholds.OTD_TARGET:
        otd_status = "good"
    elif otd >= Thresholds.OTD_WARNING:
        otd_status = "warning"
    else:
        otd_status = "danger"

    # Lead time = fecha entrega - PO date.
    lead_time = pd.Series(dtype="float64")
    if PO_DATE_COL in df.columns and FECHA_ENTREGA_COL in df.columns:
        lead_time = (df[FECHA_ENTREGA_COL] - df[PO_DATE_COL]).dt.days
        lead_time = lead_time[(lead_time.notna()) & (lead_time >= 0)]
    lead_time_promedio = float(lead_time.mean()) if not lead_time.empty else 0.0
    if len(lead_time) >= 4:
        baseline = float(lead_time.quantile(0.5))
    else:
        baseline = lead_time_promedio
    lead_time_delta_pct = ((lead_time_promedio - baseline) / baseline * 100.0) if baseline > 0 else 0.0

    if lead_time_delta_pct <= 0:
        lead_time_status = "good"
    elif lead_time_delta_pct <= Thresholds.LEAD_TIME_WARNING_PCT:
        lead_time_status = "warning"
    else:
        lead_time_status = "danger"

    # Backlog en riesgo financiero = pendiente vencido o por vencer en N dias.
    lookahead = today + pd.Timedelta(days=Thresholds.RISK_LOOKAHEAD_DAYS)
    backlog_mask = (~delivered_mask)
    if FECHA_ENTREGA_COL in df.columns:
        backlog_mask &= df[FECHA_ENTREGA_COL].notna() & (df[FECHA_ENTREGA_COL] <= lookahead)

    backlog_risk = float(df.loc[backlog_mask, Columns.TOTAL].sum()) if Columns.TOTAL in df.columns else 0.0
    backlog_orders = int(backlog_mask.sum())

    backlog_status = "good"
    if backlog_orders > 0 and monto_total > 0:
        risk_pct = backlog_risk / monto_total * 100.0
        if risk_pct >= Thresholds.CAPITAL_ATADO_WARNING_PCT:
            backlog_status = "danger"
        elif risk_pct >= 20.0:
            backlog_status = "warning"

    if "danger" in (otd_status, lead_time_status, backlog_status):
        estado_global = "Critico"
    elif "warning" in (otd_status, lead_time_status, backlog_status):
        estado_global = "En Riesgo"
    else:
        estado_global = "Estable"

    return KPISnapshot(
        total_qty=total_qty,
        total_entregados = total_entregados,
        por_entregar=por_entregar,
        monto_total=monto_total,
        otd=otd,
        otd_due_count=due_count,
        otd_on_time_count=on_time_count,
        otd_target=Thresholds.OTD_TARGET,
        otd_status=otd_status,
        lead_time_promedio_dias=lead_time_promedio,
        lead_time_delta_pct=lead_time_delta_pct,
        lead_time_status=lead_time_status,
        backlog_riesgo_financiero=backlog_risk,
        backlog_riesgo_ordenes=backlog_orders,
        backlog_status=backlog_status,
        estado_global=estado_global,
        record_count=len(df),
    )


# ---------------------------------------------------------------------------
# Distribuciones para gráficos
# ---------------------------------------------------------------------------

def group_by_ingeniero(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa Qty vs Entregados por Ingeniero.
    Retorna un DataFrame en formato largo (melted) listo para Altair.
    """
    if Columns.INGENIERO not in df.columns:
        return pd.DataFrame()

    agg = (
        df.groupby(Columns.INGENIERO)[[Columns.QTY, Columns.ENTREGADOS]]
        .sum()
        .reset_index()
    )
    melted = agg.melt(
        id_vars=Columns.INGENIERO,
        value_vars=[Columns.QTY, Columns.ENTREGADOS],
        var_name="Estado",
        value_name="Unidades",
    )
    return melted


def group_by_planeador(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa carga por planeador y conserva columna Qty para compatibilidad."""
    if Columns.PLANEADOR not in df.columns:
        return pd.DataFrame()

    if Columns.QTY not in df.columns:
        return pd.DataFrame()

    grouped = (
        df.groupby(Columns.PLANEADOR)
        .agg(
            CantidadSolicitada=(Columns.QTY, "sum"),
            CargaPendiente=(Columns.POR_ENTREGAR, "sum") if Columns.POR_ENTREGAR in df.columns else (Columns.QTY, "sum"),
        )
        .reset_index()
        .sort_values("CantidadSolicitada", ascending=False)
    )
    return grouped


def group_by_condicion(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa Qty total por Condición (estatus de entrega)."""
    cond_col = Columns.CONDICION if Columns.CONDICION in df.columns else Columns.CONDICION_ALT
    if cond_col not in df.columns or Columns.QTY not in df.columns:
        return pd.DataFrame()

    return (
        df.groupby(cond_col)[Columns.QTY]
        .sum()
        .reset_index()
        .rename(columns={cond_col: Columns.CONDICION})
    )


def top_descriptions(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Retorna los N racks con mayor demanda por descripción."""
    if Columns.DESCRIPTION not in df.columns or Columns.QTY not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work[Columns.DESCRIPTION] = work[Columns.DESCRIPTION].astype(str).str.strip()

    return (
        work.groupby(Columns.DESCRIPTION)[Columns.QTY]
        .sum()
        .reset_index()
        .sort_values(Columns.QTY, ascending=False)
        .head(n)
    )


def trend_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Serie semanal con OTD y backlog en riesgo para diagnostico ejecutivo."""
    if df.empty or FECHA_ENTREGA_COL not in df.columns:
        return pd.DataFrame()

    work = _with_datetime_cols(df)
    work = work[work[FECHA_ENTREGA_COL].notna()].copy()
    if work.empty:
        return pd.DataFrame()

    work["Week"] = work[FECHA_ENTREGA_COL].dt.to_period("W").dt.start_time
    work["Delivered"] = _is_delivered(work)
    work["Due"] = 1

    # Backlog en riesgo: pendiente y con fecha de entrega vencida o por vencer en ventana.
    today = pd.Timestamp.now().normalize()
    lookahead = today + pd.Timedelta(days=Thresholds.RISK_LOOKAHEAD_DAYS)
    risk_mask = (~work["Delivered"]) & (work[FECHA_ENTREGA_COL] <= lookahead)
    if Columns.TOTAL in work.columns:
        work["BacklogRiskAmount"] = pd.to_numeric(work[Columns.TOTAL], errors="coerce").fillna(0.0).where(risk_mask, 0.0)
    else:
        work["BacklogRiskAmount"] = 0.0

    weekly = (
        work.groupby("Week")
        .agg(
            Due=("Due", "sum"),
            Delivered=("Delivered", "sum"),
            BacklogRisk=("BacklogRiskAmount", "sum"),
        )
        .reset_index()
    )
    weekly["OTD"] = (weekly["Delivered"] / weekly["Due"] * 100.0).fillna(0.0)
    return weekly.sort_values("Week")


def risk_by_owner(df: pd.DataFrame, owner_col: str = Columns.PLANEADOR) -> pd.DataFrame:
    """Ranking de responsables por backlog financiero en riesgo."""
    if df.empty or owner_col not in df.columns:
        return pd.DataFrame()

    work = _with_datetime_cols(df)
    today = pd.Timestamp.now().normalize()
    lookahead = today + pd.Timedelta(days=Thresholds.RISK_LOOKAHEAD_DAYS)
    delivered_mask = _is_delivered(work)

    risk_mask = ~delivered_mask
    if FECHA_ENTREGA_COL in work.columns:
        risk_mask &= work[FECHA_ENTREGA_COL].notna() & (work[FECHA_ENTREGA_COL] <= lookahead)

    if Columns.TOTAL not in work.columns:
        return pd.DataFrame()

    out = (
        work.loc[risk_mask]
        .groupby(owner_col)
        .agg(
            RiesgoFinanciero=(Columns.TOTAL, "sum"),
            Ordenes=(owner_col, "count"),
            CargaPendiente=(Columns.POR_ENTREGAR, "sum") if Columns.POR_ENTREGAR in work.columns else (Columns.QTY, "sum"),
        )
        .reset_index()
        .sort_values("RiesgoFinanciero", ascending=False)
    )
    return out


def prioritized_actions(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Tabla accionable priorizada para seguimiento diario."""
    if df.empty:
        return pd.DataFrame()

    work = _with_datetime_cols(df)

    if "Entrega (Normalizada)" in work.columns:
        work.rename(columns={"Entrega (Normalizada)": "Entrega"}, inplace=True)

    if FECHA_ENTREGA_COL in work.columns and "Entrega" not in work.columns:
        work.rename(columns={FECHA_ENTREGA_COL: "Entrega"}, inplace=True)

    if "Entrega" in work.columns:
        work["Entrega"] = pd.to_datetime(work["Entrega"], errors="coerce").dt.date

    entrega_col = "Entrega" if "Entrega" in work.columns else FECHA_ENTREGA_COL

    delivered_mask = _is_delivered(work)
    today = pd.Timestamp.now().normalize()

    work = work.loc[~delivered_mask].copy()
    if work.empty:
        return pd.DataFrame()

    if entrega_col in work.columns:
        # Positivo = dias vencidos / Negativo = dias restantes
        # NaN = fecha de entrega ausente/invalida
        entrega_ts = pd.to_datetime(work[entrega_col], errors="coerce")
        work["DiasAtraso"] = (today - entrega_ts).dt.days
    else:
        work["DiasAtraso"] = pd.NA

    work["MontoRiesgo"] = work[Columns.TOTAL] if Columns.TOTAL in work.columns else 0.0
    def _accion_sugerida(dias):
        if pd.isna(dias):
            return "Completar fecha de entrega"
        if dias > 0:
            return "Escalar hoy con planeador"
        return "Confirmar fecha y capacidad"

    work["AccionSugerida"] = work["DiasAtraso"].apply(_accion_sugerida)

    columns = [
        col for col in [
            PO_COL,
            ITEM_COL,
            getattr(Columns, "RA", "RA"),
            Columns.DESCRIPTION,
            Columns.PLANEADOR,
            Columns.INGENIERO,
            entrega_col,
            Columns.POR_ENTREGAR,
            "DiasAtraso",
            "MontoRiesgo",
            "AccionSugerida",
        ] if col in work.columns or col in ["DiasAtraso", "MontoRiesgo", "AccionSugerida"]
    ]

    order_cols: list[str] = []
    ascending: list[bool] = []

    if entrega_col in work.columns:
        order_cols.append(entrega_col)
        ascending.append(True)

    order_cols.extend(["DiasAtraso", "MontoRiesgo"])
    ascending.extend([False, False])

    return (
        work[columns]
        .sort_values(order_cols, ascending=ascending, na_position="last")
        .head(top_n)
        .reset_index(drop=True)
    )


def planning_rebalance_candidates(df: pd.DataFrame, top_n: int = 3) -> tuple[pd.DataFrame, dict]:
    """Detecta cuello de botella y propone ordenes candidatas para mover a Linea 2."""
    if df.empty:
        return pd.DataFrame(), {
            "indice_saturacion_max": 0.0,
            "planeador_critico": "-",
            "ordenes_fuera_ventana": 0,
            "items_concentrados": [],
            "alerta": "Sin datos para evaluar capacidad.",
        }

    work = _with_datetime_cols(df)
    delivered_mask = _is_delivered(work)
    today = pd.Timestamp.now().normalize()

    work = work.loc[~delivered_mask].copy()
    if work.empty:
        return pd.DataFrame(), {
            "indice_saturacion_max": 0.0,
            "planeador_critico": "-",
            "ordenes_fuera_ventana": 0,
            "items_concentrados": [],
            "alerta": "No hay backlog pendiente en ventana operativa.",
        }

    if Columns.POR_ENTREGAR in work.columns:
        work["CargaPendiente"] = pd.to_numeric(work[Columns.POR_ENTREGAR], errors="coerce").fillna(0.0)
    elif Columns.QTY in work.columns:
        work["CargaPendiente"] = pd.to_numeric(work[Columns.QTY], errors="coerce").fillna(0.0)
    else:
        work["CargaPendiente"] = 0.0

    if FECHA_ENTREGA_COL in work.columns:
        work["DiasAtraso"] = (today - work[FECHA_ENTREGA_COL]).dt.days
    else:
        work["DiasAtraso"] = pd.NA

    planeador_col = Columns.PLANEADOR if Columns.PLANEADOR in work.columns else None
    if planeador_col is None:
        work["_PlaneadorProxy"] = "Sin planeador"
        planeador_col = "_PlaneadorProxy"

    load_by_planeador = (
        work.groupby(planeador_col, dropna=False)["CargaPendiente"]
        .sum()
        .reset_index(name="CargaTotal")
    )

    capacidad_referencia = float(load_by_planeador["CargaTotal"].mean()) if not load_by_planeador.empty else 0.0
    if capacidad_referencia <= 0:
        capacidad_referencia = 1.0

    load_by_planeador["IndiceSaturacion"] = load_by_planeador["CargaTotal"] / capacidad_referencia
    load_by_planeador = load_by_planeador.sort_values("IndiceSaturacion", ascending=False)

    planeador_critico = str(load_by_planeador.iloc[0][planeador_col]) if not load_by_planeador.empty else "-"
    indice_saturacion_max = float(load_by_planeador.iloc[0]["IndiceSaturacion"]) if not load_by_planeador.empty else 0.0
    planeadores_sobrecargados = load_by_planeador.loc[load_by_planeador["IndiceSaturacion"] >= 1.15, planeador_col].astype(str).tolist()

    item_hotspots: list[str] = []
    if ITEM_COL in work.columns:
        item_counts = (
            work.groupby(ITEM_COL, dropna=False)
            .size()
            .reset_index(name="Ordenes")
            .sort_values("Ordenes", ascending=False)
        )
        item_hotspots = item_counts.loc[item_counts["Ordenes"] >= 3, ITEM_COL].astype(str).tolist()

    candidates = work.copy()
    if planeadores_sobrecargados:
        candidates = candidates[candidates[planeador_col].astype(str).isin(planeadores_sobrecargados)]
    if candidates.empty:
        candidates = work.copy()

    sort_cols: list[str] = ["DiasAtraso", "CargaPendiente"]
    asc: list[bool] = [False, False]
    if FECHA_ENTREGA_COL in candidates.columns:
        sort_cols.insert(1, FECHA_ENTREGA_COL)
        asc.insert(1, True)

    candidates = candidates.sort_values(sort_cols, ascending=asc, na_position="last").head(top_n).copy()
    candidates["LineaSugerida"] = "Linea 2"
    candidates["AccionPlan"] = candidates["DiasAtraso"].apply(
        lambda d: "Mover hoy a Linea 2" if pd.notna(d) and d > 0 else "Preasignar a Linea 2"
    )

    out_cols = [
        col for col in [
            PO_COL,
            getattr(Columns, "RA", "RA"),
            ITEM_COL,
            planeador_col,
            FECHA_ENTREGA_COL,
            "DiasAtraso",
            "CargaPendiente",
            "LineaSugerida",
            "AccionPlan",
        ] if col in candidates.columns
    ]

    ordenes_fuera_ventana = int((pd.to_numeric(work["DiasAtraso"], errors="coerce") > 0).fillna(False).sum())
    alerta = (
        f"Alerta de Planificacion: {ordenes_fuera_ventana} ordenes fuera de ventana. "
        f"Planeador critico: {planeador_critico} (indice {indice_saturacion_max:.2f}x)."
    )

    return candidates[out_cols].reset_index(drop=True), {
        "indice_saturacion_max": indice_saturacion_max,
        "planeador_critico": planeador_critico,
        "ordenes_fuera_ventana": ordenes_fuera_ventana,
        "items_concentrados": item_hotspots,
        "alerta": alerta,
    }
