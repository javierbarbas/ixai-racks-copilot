from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


EXPECTED_SHEET_NAME = "Tabla1"
EXPECTED_COLUMNS = [
    "Item",
    "Costo Unitario",
    "Total",
    "Condición",
    "Peso",
    "Dimensiones",
    "Cubicaje",
    "RA",
    "Lison",
    "Ingeniero",
    "Planeador",
    "Description",
    "PO",
    "PO Date",
    "Qty.",
    "Entregados",
    "Por Entregar",
    "Fecha de Entrega",
    "%",
]

NUMERIC_COLUMNS = [
    "Item",
    "Costo Unitario",
    "Total",
    "Peso",
    "Cubicaje",
    "Qty.",
    "Entregados",
    "Por Entregar",
    "%",
]

DATE_COLUMNS = ["PO Date"]

CURRENT_YEAR = 2026
CURRENT_ISO_WEEK = 27


@dataclass(frozen=True)
class EtlPaths:
    project_root: Path
    excel_path: Path
    raw_dir: Path
    duckdb_path: Path


def default_paths(project_root: Path) -> EtlPaths:
    data_dir = project_root / "data"
    return EtlPaths(
        project_root=project_root,
        excel_path=data_dir / "data_produccion.xlsx",
        raw_dir=data_dir / "raw",
        duckdb_path=data_dir / "warehouse.duckdb",
    )