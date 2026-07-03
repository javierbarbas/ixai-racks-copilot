from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

import src.dashboard.v2_common as v2


v2.configure_page("IxAI Racks Copilot | Operacion Semanal")
bundle = v2.load_bundle()
filters = v2.render_sidebar(bundle["estado_actual"])
filtered = v2.apply_filters(bundle["estado_actual"], filters)
v2.render_operacion_semanal(filtered)