from src.core.state import AgentState
from src.core.llm import call_llm

def format_response(state: AgentState) -> dict:
    """
    Nodo de formateo de respuesta.
    Traduce los resultados tabulares de DuckDB a un formato conversacional claro.
    """
    user_question = state.get("user_question", "")
    sql_query = state.get("sql_query", "")
    sql_results = state.get("sql_results", None)
    execution_error = state.get("execution_error", None)
    validation_error = state.get("validation_error", None)
    
    system_instruction = (
        "Eres el Copiloto Analítico de IxAI Research Lab.\n"
        "Tu tarea es responder la pregunta del usuario utilizando los datos reales devueltos por la base de datos local.\n"
        "REGLAS:\n"
        "1. Sé conciso, profesional y directo al grano.\n"
        "2. Usa formato Markdown (negrita, viñetas, tablas) para hacer la lectura rápida y atractiva.\n"
        "3. Destaca los números clave y métricas importantes.\n"
        "4. Si la consulta falló por seguridad o error de ejecución, explícalo de manera clara y amigable."
    )
    
    # Manejar caso de error de seguridad
    if validation_error:
        prompt = f"""
Pregunta del usuario: "{user_question}"
Estado del sistema: La consulta fue rechazada por motivos de seguridad.
Detalle del error de seguridad: {validation_error}

Por favor, redacta una respuesta explicando al usuario que su consulta no pudo ser procesada debido a restricciones de seguridad (por ejemplo, porque implicaba modificar datos o esquemas).
"""
    # Manejar caso de error de ejecución después de agotar reintentos
    elif execution_error:
        prompt = f"""
Pregunta del usuario: "{user_question}"
Estado del sistema: Ocurrió un error al ejecutar la consulta SQL en la base de datos tras múltiples intentos.
Consulta SQL fallida: {sql_query}
Detalle del error técnico: {execution_error}

Por favor, redacta una respuesta explicando de forma amigable que hubo un problema técnico al analizar los datos y sugiere cómo el usuario podría replantear su pregunta.
"""
    # Manejar caso sin resultados
    elif sql_results is None or len(sql_results) == 0:
        prompt = f"""
Pregunta del usuario: "{user_question}"
Consulta SQL ejecutada: {sql_query}
Resultado de la consulta: [No se encontraron registros]

Redacta una respuesta explicando al usuario de forma clara que no se encontraron datos que coincidan con los criterios consultados en la base de datos.
"""
    # Flujo exitoso
    else:
        # Dar formato visual a los resultados como una lista de strings para el prompt
        results_str = ""
        # Limitar la inserción de resultados si el dataset es muy grande para no saturar el contexto
        max_rows_for_prompt = 25
        truncated = len(sql_results) > max_rows_for_prompt
        rows_to_show = sql_results[:max_rows_for_prompt]
        
        for idx, row in enumerate(rows_to_show):
            row_items = [f"{col}: {val}" for col, val in row.items()]
            results_str += f"Fila {idx+1}: " + ", ".join(row_items) + "\n"
            
        if truncated:
            results_str += f"... (y {len(sql_results) - max_rows_for_prompt} registros adicionales)\n"
            
        prompt = f"""
Pregunta del usuario: "{user_question}"
Consulta SQL ejecutada: {sql_query}
Registros devueltos por la base de datos:
{results_str}

Por favor, analiza estos datos y genera una respuesta directa en lenguaje natural respondiendo detalladamente la pregunta del usuario.
Si es pertinente, presenta los datos resumidos en una pequeña tabla Markdown o lista con viñetas.
"""

    try:
        natural_response = call_llm(prompt=prompt, system_instruction=system_instruction)
    except Exception as e:
        natural_response = f"Error al formatear la respuesta del asistente: {str(e)}"
        
    return {
        "natural_response": natural_response
    }
