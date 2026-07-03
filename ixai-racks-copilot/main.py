from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


def _configure_import_path() -> None:
    """
    Resuelve layouts distintos en despliegue (local/Hugging Face):
    - /app/main.py + /app/src/...
    - /app/main.py + /app/ixai-racks-copilot/src/...
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here,
        here / "ixai-racks-copilot",
        here.parent,
        Path("/app"),
        Path("/app") / "ixai-racks-copilot",
    ]

    for candidate in candidates:
        if (candidate / "src" / "dashboard" / "v2_common.py").exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
            return

    # Fallback: mantener comportamiento previo en el directorio del script.
    here_str = str(here)
    if here_str not in sys.path:
        sys.path.insert(0, here_str)


_configure_import_path()

from src.dashboard.v2_common import (
    apply_filters,
    configure_page,
    load_bundle,
    render_captura_datos,
    render_detalle,
    render_nl2sql_shell,
    render_operacion_semanal,
    render_resumen_ejecutivo,
    render_sidebar,
)


def main() -> None:
    configure_page("IxAI Racks Copilot | Resumen Ejecutivo")
    try:
        bundle = load_bundle()
    except Exception as exc:
        st.error(f"No fue posible cargar DuckDB: {exc}")
        return

    filters = render_sidebar(bundle["estado_actual"])
    filtered = apply_filters(bundle["estado_actual"], filters)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "1. Resumen Ejecutivo",
            "2. Operacion Semanal",
            "3. Detalle por PO / Planeador",
            "4. Pregunta a tus Datos",
            "5. Captura de Datos",
        ]
    )

    with tab1:
        render_resumen_ejecutivo(filtered, bundle["historico"])

    with tab2:
        render_operacion_semanal(filtered)

    with tab3:
        render_detalle(filtered)

    with tab4:
        render_nl2sql_shell(filtered, bundle["historico"])

    with tab5:
        render_captura_datos()


if __name__ == "__main__":
    main()
