from __future__ import annotations

from src.dashboard.v2_common import apply_filters, configure_page, load_bundle, render_detalle, render_sidebar


configure_page("IxAI Racks Copilot | Detalle")
bundle = load_bundle()
filters = render_sidebar(bundle["estado_actual"])
filtered = apply_filters(bundle["estado_actual"], filters)
render_detalle(filtered)