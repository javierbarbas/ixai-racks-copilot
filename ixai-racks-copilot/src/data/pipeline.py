"""Pipeline de normalizacion para separacion operativa y casos especiales."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import pandas as pd

from src.config.constants import Columns


@dataclass
class PipelineResult:
    """Salida estructurada del pipeline de carga."""

    operational_df: pd.DataFrame
    special_cases_df: pd.DataFrame
    dropped_columns: list[str]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_candidates = {
        "Qty": Columns.QTY,
        "QTY": Columns.QTY,
        "qty": Columns.QTY,
        "cantidad_producida": Columns.QTY,
        Columns.CONDICION_ALT: Columns.CONDICION,
        "Condicion ": Columns.CONDICION,
        "Descripcion": Columns.DESCRIPTION,
        "Descripción": Columns.DESCRIPTION,
        "modelo_rack": Columns.DESCRIPTION,
    }

    to_rename: dict[str, str] = {}
    for source, target in rename_candidates.items():
        if source in df.columns and target not in df.columns:
            to_rename[source] = target

    if to_rename:
        return df.rename(columns=to_rename)
    return df


def _drop_full_null_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dropped = [col for col in df.columns if df[col].isna().all()]
    if not dropped:
        return df, dropped
    return df.drop(columns=dropped), dropped


def _cast_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in Columns.NUMERIC_COLS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    return out


def _resolve_calendar_path(calendar_path: str | None = None) -> str:
    if calendar_path:
        return calendar_path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "data", "Calendario_Produccion_2026.csv")


def load_calendar_reference(calendar_path: str | None = None) -> pd.DataFrame:
    """Carga la tabla de referencia Semana/Ano/Fecha_Lunes_Inicio."""
    path = _resolve_calendar_path(calendar_path)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Calendario de produccion no encontrado: {path}. "
            "Genera o agrega Calendario_Produccion_2026.csv antes de ejecutar el pipeline."
        )

    cal = pd.read_csv(path)
    required = {"Semana", "Año", "Fecha_Lunes_Inicio"}
    missing = required.difference(cal.columns)
    if missing:
        raise ValueError(f"Calendario invalido. Faltan columnas: {sorted(missing)}")

    cal = cal.copy()
    cal["Semana"] = pd.to_numeric(cal["Semana"], errors="coerce").astype("Int64")
    cal["Año"] = pd.to_numeric(cal["Año"], errors="coerce").astype("Int64")
    cal["Fecha_Lunes_Inicio"] = pd.to_datetime(cal["Fecha_Lunes_Inicio"], errors="coerce")
    cal = cal.dropna(subset=["Semana", "Año", "Fecha_Lunes_Inicio"]).reset_index(drop=True)
    return cal


def _extract_week_num(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(?i)semana\s*(\d{1,2})", text)
    if not match:
        return None
    week = int(match.group(1))
    if week < 1 or week > 53:
        return None
    return float(week)


def apply_operational_pipeline(
    df_raw: pd.DataFrame,
    operating_year: int = 2026,
    calendar_path: str | None = None,
    treat_old_active_po_as_special: bool = True,
) -> PipelineResult:
    """Normaliza datos y separa flujo operativo 2026 de casos especiales."""
    df = _normalize_columns(df_raw)
    df, dropped_cols = _drop_full_null_columns(df)
    df = _cast_numeric_columns(df)

    if Columns.PO_DATE in df.columns:
        df[Columns.PO_DATE] = pd.to_datetime(df[Columns.PO_DATE], errors="coerce")

    cal = load_calendar_reference(calendar_path)
    cal = cal[cal["Año"] == operating_year].copy()
    week_to_date = dict(zip(cal["Semana"].astype(int), cal["Fecha_Lunes_Inicio"]))

    df = df.copy()
    week_num = df[Columns.FECHA_ENTREGA].apply(_extract_week_num) if Columns.FECHA_ENTREGA in df.columns else pd.Series([None] * len(df), index=df.index)
    df["Semana_Entrega"] = pd.to_numeric(week_num, errors="coerce").astype("Int64")
    df["Fecha_Entrega_Normalizada"] = df["Semana_Entrega"].map(week_to_date)
    if Columns.FECHA_ENTREGA in df.columns:
        raw_delivery = df[Columns.FECHA_ENTREGA].astype("string").str.strip()
        non_week_mask = ~raw_delivery.str.contains(r"(?i)semana\s*\d{1,2}", na=False)
        direct_dates = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
        if non_week_mask.any():
            direct_dates.loc[non_week_mask] = pd.to_datetime(
                raw_delivery.loc[non_week_mask],
                errors="coerce",
                dayfirst=True,
            )
        df["Fecha_Entrega_Normalizada"] = df["Fecha_Entrega_Normalizada"].fillna(direct_dates)

    if Columns.CONDICION in df.columns:
        df[Columns.CONDICION] = df[Columns.CONDICION].astype(str).str.strip()

    reasons = pd.Series("", index=df.index, dtype="string")
    po_date_year = df[Columns.PO_DATE].dt.year if Columns.PO_DATE in df.columns else pd.Series([pd.NA] * len(df), index=df.index)

    if treat_old_active_po_as_special:
        active_old_po = (
            (po_date_year < operating_year)
            & (pd.to_numeric(df.get(Columns.POR_ENTREGAR, 0), errors="coerce").fillna(0) > 0)
        )
        reasons = reasons.mask(active_old_po, "PO historica activa")

    missing_delivery_date = df["Fecha_Entrega_Normalizada"].isna()
    reasons = reasons.mask(missing_delivery_date & reasons.eq(""), "Sin fecha de entrega normalizada")

    out_of_year = (
        df["Fecha_Entrega_Normalizada"].notna()
        & (df["Fecha_Entrega_Normalizada"].dt.year != operating_year)
    )
    reasons = reasons.mask(out_of_year & reasons.eq(""), "Entrega fuera de anio operativo")

    special_mask = reasons.ne("")
    special_df = df.loc[special_mask].copy()
    special_df["CasoEspecial"] = reasons.loc[special_mask].astype(str)

    operational_mask = (
        ~special_mask
        & df["Fecha_Entrega_Normalizada"].notna()
        & (df["Fecha_Entrega_Normalizada"].dt.year == operating_year)
    )
    operational_df = df.loc[operational_mask].copy()
    if Columns.FECHA_ENTREGA in operational_df.columns:
        operational_df[Columns.FECHA_ENTREGA] = operational_df["Fecha_Entrega_Normalizada"]

    return PipelineResult(
        operational_df=operational_df.reset_index(drop=True),
        special_cases_df=special_df.reset_index(drop=True),
        dropped_columns=dropped_cols,
    )
