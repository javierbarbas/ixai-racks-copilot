import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

class Config:
    EXCEL_DATA_PATH = os.getenv("EXCEL_DATA_PATH", "data/produccion_racks.xlsx")

    # Elegir qué modelo usar por defecto — evaluado en tiempo de ejecución vía propiedad
    DEFAULT_LLM_PROVIDER = "groq"

    @staticmethod
    def _to_bool(value: str | None, default: bool = False) -> bool:
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "y", "si", "on"}

    @classmethod
    def get_operating_year(cls) -> int:
        """Año operativo usado para separar flujo normal y casos especiales."""
        raw = os.getenv("OPERATING_YEAR", "").strip()
        if raw.isdigit():
            return int(raw)
        return datetime.now().year

    @classmethod
    def get_calendar_reference_path(cls) -> str | None:
        """Ruta opcional del calendario de referencia Semana->Fecha."""
        path = os.getenv("CALENDAR_REFERENCE_PATH", "").strip()
        return path or None

    @classmethod
    def include_special_cases_panel(cls) -> bool:
        """Controla si se muestra el panel de casos especiales en UI."""
        return cls._to_bool(os.getenv("SHOW_SPECIAL_CASES", "true"), default=True)

    @classmethod
    def treat_old_active_po_as_special(cls) -> bool:
        """Si es true, POs historicas activas salen del KPI operativo."""
        return cls._to_bool(os.getenv("TREAT_OLD_ACTIVE_PO_AS_SPECIAL", "true"), default=True)

    @classmethod
    def get_groq_api_key(cls) -> str:
        """Lee GROQ_API_KEY en tiempo de ejecución (no al importar el módulo)."""
        return os.getenv("GROQ_API_KEY", "").strip()

    @classmethod
    def get_gemini_api_key(cls) -> str:
        """Lee GEMINI_API_KEY en tiempo de ejecución (no al importar el módulo)."""
        return os.getenv("GEMINI_API_KEY", "").strip()

    @classmethod
    def validate_config(cls):
        """
        Valida que al menos una clave API de LLM esté configurada.
        Lee os.getenv() en tiempo de llamada — no usa atributos de clase congelados
        al momento del import, lo que elimina el bug de timing cuando Streamlit
        ya está corriendo y el .env se actualiza.
        """
        groq_key   = cls.get_groq_api_key()
        gemini_key = cls.get_gemini_api_key()

        if not groq_key and not gemini_key:
            raise ValueError(
                "Configuración incompleta: define GROQ_API_KEY o GEMINI_API_KEY en el archivo .env"
            )
