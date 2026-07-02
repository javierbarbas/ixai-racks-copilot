import re
from src.core.state import AgentState
from src.core.llm import call_llm
from src.db.connection import get_schema_info

def clean_sql_query(sql_text: str) -> str:
    """
    Limpia cualquier formato de markdown o texto extra de la respuesta de la API.
    """
    # Eliminar bloques de código markdown como ```sql o ```
    cleaned = re.sub(r"```sql\s*", "", sql_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    # Eliminar cualquier punto y coma al final si existe
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned

def generate_sql(state: AgentState) -> dict:
    """
    Nodo del grafo que traduce la consulta del usuario a código SQL de DuckDB, 
    usando el esquema de la base de datos y la historia de errores si existe un reintento.
    """
    user_question = state.get("user_question", "")
    attempt = state.get("attempt_count", 0)
    execution_error = state.get("execution_error", None)
    validation_error = state.get("validation_error", None)
    
    # Obtener el esquema actualizado de la base de datos
    schema_info = get_schema_info()
    
    system_instruction = (
        "Eres un traductor experto de Lenguaje Natural a SQL especializado en DuckDB.\n"
        "Tu única tarea es generar una consulta SQL SELECT válida y eficiente para DuckDB.\n"
        "REGLA CRÍTICA: Devuelve ÚNICAMENTE la consulta SQL cruda. No incluyas comentarios, "
        "no utilices markdown (como ```sql), ni des explicaciones adicionales. La salida debe ser ejecutable directamente."
    )
    
    prompt = f"""
Aquí está el esquema de la base de datos sobre la cual debes realizar la consulta:
{schema_info}

Pregunta del usuario: "{user_question}"
"""
    
    # Inyectar información de error de reintentos anteriores si existen
    if attempt > 0 and (execution_error or validation_error):
        error_msg = execution_error if execution_error else validation_error
        prompt += f"""
AVISO DE ERROR EN INTENTO ANTERIOR:
La consulta SQL que generaste previamente falló. 
El error fue: {error_msg}

Por favor, corrige la consulta SQL. Asegúrate de:
1. Usar únicamente nombres de columnas que existan exactamente en el esquema listado arriba.
2. Evitar errores de agregación, sintaxis o tipos de datos de DuckDB.
3. Asegurarte de que sea un SELECT válido y seguro.
"""

    try:
        response = call_llm(prompt=prompt, system_instruction=system_instruction)
        sql_query = clean_sql_query(response)
    except Exception as e:
        sql_query = f"SELECT ERROR: {str(e)}"
        
    return {
        "sql_query": sql_query,
        "attempt_count": attempt + 1,
        # Limpiamos los errores anteriores en este nodo ya que estamos generando una nueva consulta
        "execution_error": None,
        "validation_error": None,
        "schema_info": schema_info
    }
