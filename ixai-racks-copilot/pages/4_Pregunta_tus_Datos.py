from __future__ import annotations

from src.dashboard.v2_common import apply_filters, configure_page, load_bundle, render_nl2sql_shell, render_sidebar


configure_page("IxAI Racks Copilot | Pregunta a tus Datos")
bundle = load_bundle()
filters = render_sidebar(bundle["estado_actual"])
filtered = apply_filters(bundle["estado_actual"], filters)
render_nl2sql_shell(filtered, bundle["historico"])