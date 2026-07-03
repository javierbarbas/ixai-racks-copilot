from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.v2_common import configure_page, render_captura_datos


configure_page("IxAI Racks Copilot | Captura de Datos")
render_captura_datos()
