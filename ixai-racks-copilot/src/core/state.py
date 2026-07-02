from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """
    Representa el estado que fluye a través de los nodos del grafo en LangGraph.
    """
    # Pregunta o consulta ingresada por el usuario
    user_question: str
    
    # Decisión de enrutamiento tomada por el router ("greeting", "visualize", "query")
    routing_decision: Optional[str]
    
    # Consulta SQL generada
    sql_query: Optional[str]
    
    # Indica si la consulta SQL es segura y válida
    query_valid: bool
    
    # Mensaje de error detallado de la validación
    validation_error: Optional[str]
    
    # Resultados de la ejecución SQL de DuckDB (lista de registros)
    sql_results: Optional[List[Dict[str, Any]]]
    
    # Mensaje de error de ejecución SQL si falla DuckDB
    execution_error: Optional[str]
    
    # Respuesta final en lenguaje natural generada para el usuario
    natural_response: Optional[str]
    
    # Número de intentos realizados para corregir una query fallida (máximo 2)
    attempt_count: int
    
    # Información del esquema de la base de datos (tablas y columnas)
    schema_info: Optional[str]
