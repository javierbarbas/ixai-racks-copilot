from __future__ import annotations

import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from schema_contract import (
    CURRENT_ISO_WEEK,
    CURRENT_YEAR,
    DATE_COLUMNS,
    EXPECTED_COLUMNS,
    EXPECTED_SHEET_NAME,
    EtlPaths,
    NUMERIC_COLUMNS,
    default_paths,
)


class SchemaValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestResult:
    excel_path: str
    duckdb_path: str
    snapshot_path: str
    rows_estado_actual: int
    rows_historico_inserted: int
    distinct_pos: int
    distinct_planeadores: int
    snapshot_ts: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_directories(paths: EtlPaths) -> None:
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    paths.duckdb_path.parent.mkdir(parents=True, exist_ok=True)


def _copy_raw_snapshot(paths: EtlPaths, snapshot_ts: pd.Timestamp) -> Path:
    stamp = snapshot_ts.strftime("%Y%m%d_%H%M%S")
    snapshot_path = paths.raw_dir / f"data_produccion_{stamp}.xlsx"
    shutil.copy2(paths.excel_path, snapshot_path)
    return snapshot_path


def _load_source_dataframe(paths: EtlPaths) -> pd.DataFrame:
    if not paths.excel_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo fuente: {paths.excel_path}")

    workbook = pd.ExcelFile(paths.excel_path)
    if EXPECTED_SHEET_NAME not in workbook.sheet_names:
        raise SchemaValidationError(
            f"La hoja requerida '{EXPECTED_SHEET_NAME}' no existe. Hojas detectadas: {workbook.sheet_names}"
        )

    df = pd.read_excel(paths.excel_path, sheet_name=EXPECTED_SHEET_NAME, engine="openpyxl")
    _validate_schema(df)
    return df


def _validate_schema(df: pd.DataFrame) -> None:
    actual_columns = list(df.columns)
    missing = [column for column in EXPECTED_COLUMNS if column not in actual_columns]
    unexpected = [column for column in actual_columns if column not in EXPECTED_COLUMNS]

    if missing or unexpected:
        messages: list[str] = []
        if missing:
            messages.append(f"Columnas faltantes: {missing}")
        if unexpected:
            messages.append(f"Columnas inesperadas: {unexpected}")
        raise SchemaValidationError("; ".join(messages))


def _normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    for column in NUMERIC_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    for column in DATE_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_datetime(normalized[column], errors="coerce")

    for column in normalized.columns:
        if column not in NUMERIC_COLUMNS and column not in DATE_COLUMNS:
            normalized[column] = normalized[column].where(normalized[column].notna(), None)

    return normalized


def _extract_delivery_week(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    match = re.search(r"(?i)semana\s*(\d{1,2})", text)
    if not match:
        return None
    week_num = int(match.group(1))
    if week_num < 1 or week_num > 53:
        return None
    return week_num


def _resolve_delivery_year(week_num: int | None, po_date: pd.Timestamp | None) -> int | None:
    if week_num is None:
        return None

    if po_date is not None and not pd.isna(po_date):
        po_week = int(po_date.isocalendar().week)
        po_year = int(po_date.year)
        return po_year + 1 if week_num < po_week else po_year

    return CURRENT_YEAR


def _to_iso_monday(year: int | None, week_num: int | None) -> pd.Timestamp:
    if year is None or week_num is None:
        return pd.NaT
    try:
        return pd.Timestamp.fromisocalendar(int(year), int(week_num), 1)
    except ValueError:
        return pd.NaT


def _derive_status(entregados: float, qty: float, por_entregar: float) -> str:
    qty_value = float(qty or 0)
    entregados_value = float(entregados or 0)
    por_entregar_value = float(por_entregar or 0)

    if qty_value <= 0:
        return "Sin iniciar"
    if por_entregar_value <= 0:
        return "Completo"
    if 0 < entregados_value < qty_value:
        return "Parcial"
    return "Sin iniciar"


def _derive_urgency(fecha_entrega_real: pd.Timestamp, today: pd.Timestamp) -> str:
    if pd.isna(fecha_entrega_real):
        return "Sin fecha"

    delivery = fecha_entrega_real.normalize()
    current_week_start = today - pd.Timedelta(days=today.weekday())
    next_two_weeks_end = current_week_start + pd.Timedelta(days=20)

    if delivery < current_week_start:
        return "Vencida"
    if current_week_start <= delivery <= current_week_start + pd.Timedelta(days=6):
        return "Semana actual"
    if delivery <= next_two_weeks_end:
        return "Proximas 2 semanas"
    return "Futura"


def _transform(df: pd.DataFrame, snapshot_ts: pd.Timestamp) -> pd.DataFrame:
    transformed = _normalize_types(df)

    transformed["snapshot_ts"] = snapshot_ts
    transformed["delivery_week_num"] = transformed["Fecha de Entrega"].apply(_extract_delivery_week)
    transformed["semana_entrega_anio"] = transformed.apply(
        lambda row: _resolve_delivery_year(row["delivery_week_num"], row.get("PO Date")),
        axis=1,
    )
    transformed["fecha_entrega_real"] = transformed.apply(
        lambda row: _to_iso_monday(row["semana_entrega_anio"], row["delivery_week_num"]),
        axis=1,
    )

    qty = pd.to_numeric(transformed["Qty."], errors="coerce").fillna(0)
    entregados = pd.to_numeric(transformed["Entregados"], errors="coerce").fillna(0)
    por_entregar_raw = pd.to_numeric(transformed["Por Entregar"], errors="coerce").fillna(0)
    por_entregar_calc = (qty - entregados).clip(lower=0)

    transformed["por_entregar_recalculado"] = por_entregar_calc
    transformed["por_entregar_consistente"] = por_entregar_raw.eq(por_entregar_calc)
    transformed["avance_real_pct"] = (entregados / qty.where(qty > 0)).fillna(0.0)
    transformed["valor_pendiente"] = pd.to_numeric(transformed["Costo Unitario"], errors="coerce").fillna(0.0) * por_entregar_calc
    transformed["valor_entregado"] = pd.to_numeric(transformed["Costo Unitario"], errors="coerce").fillna(0.0) * entregados
    transformed["estatus_real"] = [
        _derive_status(entregados_value, qty_value, por_entregar_value)
        for entregados_value, qty_value, por_entregar_value in zip(entregados, qty, por_entregar_calc)
    ]

    today = pd.Timestamp.now().normalize()
    transformed["urgencia"] = transformed["fecha_entrega_real"].apply(lambda value: _derive_urgency(value, today))
    transformed["peso_disponible"] = transformed["Peso"].notna()
    transformed["condicion_fuente_no_confiable"] = True
    transformed["etl_reference_year"] = CURRENT_YEAR
    transformed["etl_reference_week"] = CURRENT_ISO_WEEK

    return transformed


def _write_duckdb(df: pd.DataFrame, paths: EtlPaths) -> None:
    connection = duckdb.connect(str(paths.duckdb_path))
    try:
        connection.register("incoming_df", df)
        connection.execute("CREATE OR REPLACE TABLE estado_actual AS SELECT * FROM incoming_df")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS historico AS
            SELECT * FROM incoming_df WHERE 1 = 0
            """
        )
        connection.execute("INSERT INTO historico SELECT * FROM incoming_df")
    finally:
        connection.close()


def run_ingest() -> IngestResult:
    project_root = _project_root()
    paths = default_paths(project_root)
    _ensure_directories(paths)

    snapshot_ts = pd.Timestamp.now().floor("s")
    source_df = _load_source_dataframe(paths)
    transformed_df = _transform(source_df, snapshot_ts)
    snapshot_path = _copy_raw_snapshot(paths, snapshot_ts)
    _write_duckdb(transformed_df, paths)

    return IngestResult(
        excel_path=str(paths.excel_path),
        duckdb_path=str(paths.duckdb_path),
        snapshot_path=str(snapshot_path),
        rows_estado_actual=len(transformed_df),
        rows_historico_inserted=len(transformed_df),
        distinct_pos=int(transformed_df["PO"].astype(str).nunique(dropna=True)),
        distinct_planeadores=int(transformed_df["Planeador"].astype(str).nunique(dropna=True)),
        snapshot_ts=snapshot_ts.isoformat(),
    )


if __name__ == "__main__":
    result = run_ingest()
    print("ETL completado")
    for key, value in asdict(result).items():
        print(f"{key}={value}")