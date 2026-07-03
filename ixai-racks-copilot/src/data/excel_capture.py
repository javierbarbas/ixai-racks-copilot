from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from etl.schema_contract import DATE_COLUMNS, EXPECTED_COLUMNS, EXPECTED_SHEET_NAME, NUMERIC_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXCEL_PATH = PROJECT_ROOT / "data" / "data_produccion.xlsx"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _ensure_excel_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo Excel fuente: {path}")


def _normalize_capture_df(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    for column in EXPECTED_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[EXPECTED_COLUMNS].copy()

    for column in NUMERIC_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    for column in DATE_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_datetime(normalized[column], errors="coerce")

    return normalized


def load_capture_dataframe(excel_path: str | None = None) -> pd.DataFrame:
    path = Path(excel_path) if excel_path else DEFAULT_EXCEL_PATH
    _ensure_excel_exists(path)

    workbook = pd.ExcelFile(path, engine="openpyxl")
    if EXPECTED_SHEET_NAME not in workbook.sheet_names:
        raise RuntimeError(
            f"La hoja '{EXPECTED_SHEET_NAME}' no existe en {path.name}. "
            f"Hojas detectadas: {workbook.sheet_names}"
        )

    df = pd.read_excel(path, sheet_name=EXPECTED_SHEET_NAME, engine="openpyxl")
    return _normalize_capture_df(df)


def save_capture_dataframe(df: pd.DataFrame, excel_path: str | None = None) -> Path:
    path = Path(excel_path) if excel_path else DEFAULT_EXCEL_PATH
    _ensure_excel_exists(path)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = RAW_DIR / f"data_produccion_manual_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    shutil.copy2(path, backup_path)

    normalized = _normalize_capture_df(df)

    with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        normalized.to_excel(writer, sheet_name=EXPECTED_SHEET_NAME, index=False)

    return backup_path
