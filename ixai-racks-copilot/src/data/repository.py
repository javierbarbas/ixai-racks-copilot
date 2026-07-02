"""
repository.py
=============
Capa de acceso a datos.  Un solo lugar donde se lee el Excel / DuckDB.

Principio clave: los datos se cargan UNA SOLA VEZ por sesión gracias a
@st.cache_data.  Si mañana el origen cambia a Snowflake, BigQuery o una
API REST, solo se modifica esta función — el resto del proyecto no cambia.
"""

from __future__ import annotations

import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.config.constants import Columns
from src.core.config import Config
from src.data.pipeline import apply_operational_pipeline
from src.logic.metrics import with_datetime_cols

load_dotenv()

# ---------------------------------------------------------------------------
# Ruta por defecto — resolución relativa al paquete
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DEFAULT_EXCEL_PATH = os.path.join(_BASE_DIR, "data", "produccion_racks.xlsx")


# ---------------------------------------------------------------------------
# Carga con caché Streamlit — solo ejecuta I/O una vez por sesión
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="⚙️ Cargando datos de producción…")
def load_data_bundle(excel_path: str | None = None) -> dict[str, object]:
    """
    Lee el archivo Excel y retorna un DataFrame limpio.

    El decorador @st.cache_data garantiza que la lectura del disco
    ocurre una sola vez por sesión, independientemente de cuántos
    reruns dispare Streamlit.

    Parameters
    ----------
    excel_path : str | None
        Ruta al archivo Excel. Si es None se usa la variable de entorno
        EXCEL_DATA_PATH o el valor por defecto.

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas numéricas casteadas.

    Raises
    ------
    FileNotFoundError
        Si el archivo no existe en la ruta indicada.
    """
    path = excel_path or os.getenv("EXCEL_DATA_PATH", DEFAULT_EXCEL_PATH)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Archivo de datos no encontrado: {path}\n"
            "Verifica la variable EXCEL_DATA_PATH en tu archivo .env"
        )

    df_raw = pd.read_excel(path, engine="openpyxl")
    result = apply_operational_pipeline(
        df_raw,
        operating_year=Config.get_operating_year(),
        calendar_path=Config.get_calendar_reference_path(),
        treat_old_active_po_as_special=Config.treat_old_active_po_as_special(),
    )
    df_operational = with_datetime_cols(result.operational_df)

    return {
        "operational": df_operational,
        "special_cases": result.special_cases_df,
        "dropped_columns": result.dropped_columns,
    }


def load_dataframe(excel_path: str | None = None) -> pd.DataFrame:
    """Compat wrapper: retorna solo el dataset operativo 2026."""
    bundle = load_data_bundle(excel_path=excel_path)
    return bundle["operational"]


# ---------------------------------------------------------------------------
# Filtrado — aplica los filtros del sidebar al DataFrame ya cargado en caché
# ---------------------------------------------------------------------------

def apply_filters(
    df: pd.DataFrame,
    ingenieros: list[str] | None = None,
    planeadores: list[str] | None = None,
    condiciones: list[str] | None = None,
) -> pd.DataFrame:
    """
    Aplica filtros sobre el DataFrame base ya cacheado.
    Solo recorre el DataFrame una vez, combinando todas las máscaras.

    Parameters
    ----------
    df          : DataFrame base (sin filtrar).
    ingenieros  : Lista de ingenieros seleccionados; None = todos.
    planeadores : Lista de planeadores seleccionados; None = todos.
    condiciones : Lista de condiciones seleccionadas; None = todas.

    Returns
    -------
    pd.DataFrame filtrado.
    """
    mask = pd.Series(True, index=df.index)

    if ingenieros and Columns.INGENIERO in df.columns:
        mask &= df[Columns.INGENIERO].isin(ingenieros)

    if planeadores and Columns.PLANEADOR in df.columns:
        mask &= df[Columns.PLANEADOR].isin(planeadores)

    if condiciones and Columns.CONDICION in df.columns:
        mask &= df[Columns.CONDICION].isin(condiciones)

    return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Utilidad: valores únicos para los widgets del sidebar
# ---------------------------------------------------------------------------

def get_filter_options(df: pd.DataFrame) -> dict[str, list]:
    """
    Devuelve los valores únicos de cada columna filtrable,
    ordenados alfabéticamente, para poblar los multiselects del sidebar.
    """
    options: dict[str, list] = {}
    for col in [Columns.INGENIERO, Columns.PLANEADOR, Columns.CONDICION]:
        if col in df.columns:
            options[col] = sorted(df[col].dropna().unique().tolist())
    return options
