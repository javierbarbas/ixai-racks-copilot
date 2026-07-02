from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"
DEFAULT_EXCEL_PATH = PROJECT_ROOT / "data" / "data_produccion.xlsx"
INGEST_SCRIPT_PATH = PROJECT_ROOT / "etl" / "ingest.py"


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    query = "select count(*) from information_schema.tables where table_name = ?"
    return bool(connection.execute(query, [table_name]).fetchone()[0])


def _run_ingest_subprocess() -> None:
    subprocess.run(
        [sys.executable, str(INGEST_SCRIPT_PATH)],
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def _ensure_warehouse_ready(path: Path) -> None:
    """
    Prepara el warehouse en entornos nuevos (ej. Hugging Face Spaces) donde
    puede no existir el archivo DuckDB en el primer arranque.
    """
    if path.exists():
        return

    if not INGEST_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"No existe script de ingesta: {INGEST_SCRIPT_PATH}")
    if not DEFAULT_EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"No existe fuente de datos para construir DuckDB: {DEFAULT_EXCEL_PATH}"
        )

    _run_ingest_subprocess()

    if not path.exists():
        raise FileNotFoundError(f"No fue posible generar el warehouse DuckDB: {path}")


@st.cache_data(show_spinner="Cargando warehouse DuckDB...")
def load_warehouse_bundle(duckdb_path: str | None = None) -> dict[str, pd.DataFrame]:
    path = Path(duckdb_path) if duckdb_path else DEFAULT_DUCKDB_PATH
    _ensure_warehouse_ready(path)

    connection = duckdb.connect(str(path), read_only=True)
    try:
        if not _table_exists(connection, "estado_actual"):
            connection.close()
            _run_ingest_subprocess()
            connection = duckdb.connect(str(path), read_only=True)
            if not _table_exists(connection, "estado_actual"):
                raise RuntimeError("La tabla 'estado_actual' no existe en DuckDB.")

        estado_actual = connection.sql("select * from estado_actual").df()
        historico = connection.sql("select * from historico order by snapshot_ts").df() if _table_exists(connection, "historico") else pd.DataFrame()
    finally:
        connection.close()

    for column in ["PO Date", "fecha_entrega_real", "snapshot_ts"]:
        if column in estado_actual.columns:
            estado_actual[column] = pd.to_datetime(estado_actual[column], errors="coerce")
        if column in historico.columns:
            historico[column] = pd.to_datetime(historico[column], errors="coerce")

    return {"estado_actual": estado_actual, "historico": historico}


def run_ingest_refresh() -> str:
    result = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT_PATH)],
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    load_warehouse_bundle.clear()
    return result.stdout.strip()