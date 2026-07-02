from langgraph.graph import StateGraph, END
from src.core.state import AgentState
from src.skills.sql_generator import generate_sql
from src.skills.sql_validator import validate_sql
from src.skills.duckdb_executor import execute_duckdb_query
from src.skills.response_formatter import format_response

# Funciones de enrutamiento condicional

def should_after_validator(state: AgentState) -> str:
    """
    Decide la transición después de validar la seguridad de la consulta SQL.
    """
    # Si la consulta es válida, avanzamos a la ejecución
    if state.get("query_valid", False):
        return "executor"
    
    # Si no es válida y no hemos alcanzado el límite de intentos (2), reintentamos generar
    attempt = state.get("attempt_count", 0)
    if attempt < 2:
        print(f"[Validator Node] Intento {attempt} inválido por seguridad. Reintentando...")
        return "generator"
    
    # Si ya superamos el límite, vamos al formateador de respuesta para informar el error
    print(f"[Validator Node] Intento {attempt} inválido por seguridad. Límite alcanzado.")
    return "formatter"

def should_after_executor(state: AgentState) -> str:
    """
    Decide la transición después de intentar ejecutar la consulta SQL.
    """
    execution_error = state.get("execution_error", None)
    
    # Si no hay error de ejecución, vamos directamente a formatear la respuesta exitosa
    if execution_error is None:
        return "formatter"
        
    # Si hay error y tenemos intentos disponibles (< 2), volvemos a generar la SQL con el feedback
    attempt = state.get("attempt_count", 0)
    if attempt < 2:
        print(f"[Executor Node] Error de DuckDB en intento {attempt}: {execution_error}. Reintentando auto-corrección...")
        return "generator"
        
    # Si ya agotamos intentos, mostramos el error final
    print(f"[Executor Node] Error de DuckDB en intento {attempt}: {execution_error}. Límite alcanzado.")
    return "formatter"

# Construcción del grafo de estado (StateGraph)

def get_text_to_sql_graph():
    # Inicializar el grafo con el esquema del estado de agente
    workflow = StateGraph(AgentState)
    
    # Agregar los nodos atómicos (skills)
    workflow.add_node("generator", generate_sql)
    workflow.add_node("validator", validate_sql)
    workflow.add_node("executor", execute_duckdb_query)
    workflow.add_node("formatter", format_response)
    
    # Definir punto de entrada
    workflow.set_entry_point("generator")
    
    # Conectar el generador al validador de forma directa
    workflow.add_edge("generator", "validator")
    
    # Conectar validador de forma condicional
    workflow.add_conditional_edges(
        "validator",
        should_after_validator,
        {
            "executor": "executor",
            "generator": "generator",
            "formatter": "formatter"
        }
    )
    
    # Conectar ejecutor de forma condicional
    workflow.add_conditional_edges(
        "executor",
        should_after_executor,
        {
            "formatter": "formatter",
            "generator": "generator"
        }
    )
    
    # Conectar el formateador al final del grafo
    workflow.add_edge("formatter", END)
    
    # Compilar el grafo
    return workflow.compile()
