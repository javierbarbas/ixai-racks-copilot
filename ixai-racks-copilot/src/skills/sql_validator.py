import re
from src.core.state import AgentState

def validate_sql(state: AgentState) -> dict:
    """
    Nodo de validación de seguridad (Python Puro, sin IA).
    Verifica que la consulta SQL sea segura y se limite únicamente a operaciones SELECT de lectura.
    """
    sql_query = state.get("sql_query", "")
    
    if not sql_query:
        return {
            "query_valid": False,
            "validation_error": "La consulta SQL generada está vacía."
        }
        
    # Palabras clave prohibidas (modificación de datos o esquema)
    forbidden_keywords = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bUPDATE\b",
        r"\bINSERT\b",
        r"\bALTER\b",
        r"\bTRUNCATE\b",
        r"\bCREATE\b",
        r"\bREPLACE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b"
    ]
    
    # Comprobar si contiene alguna palabra prohibida (insensible a mayúsculas/minúsculas)
    sql_upper = sql_query.upper()
    
    for pattern in forbidden_keywords:
        if re.search(pattern, sql_upper):
            # Obtener la palabra prohibida del patrón para mostrarla en el error
            keyword = pattern.replace(r"\b", "")
            return {
                "query_valid": False,
                "validation_error": f"Seguridad: La consulta contiene la instrucción prohibida '{keyword}'."
            }
            
    # Asegurar que comience con SELECT (o WITH para CTEs)
    # Ignorar espacios en blanco al inicio
    query_stripped = sql_query.strip().upper()
    if not (query_stripped.startswith("SELECT") or query_stripped.startswith("WITH")):
        return {
            "query_valid": False,
            "validation_error": "Seguridad: Solo se permiten consultas SELECT o de lectura estructurada (WITH)."
        }
        
    # Si pasa todas las validaciones
    return {
        "query_valid": True,
        "validation_error": None
    }
