from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.v2_common import apply_filters, configure_page, load_bundle, render_operacion_semanal, render_sidebar


configure_page("IxAI Racks Copilot | Operacion Semanal")
bundle = load_bundle()
filters = render_sidebar(bundle["estado_actual"])
filtered = apply_filters(bundle["estado_actual"], filters)
render_operacion_semanal(filtered)