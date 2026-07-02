from src.core.state import AgentState
from src.db.connection import get_db_connection

def execute_duckdb_query(state: AgentState) -> dict:
    """
    Nodo de ejecución de consultas en DuckDB.
    Ejecuta la consulta SQL si fue validada y guarda los resultados o el error.
    """
    sql_query = state.get("sql_query", "")
    query_valid = state.get("query_valid", False)
    validation_error = state.get("validation_error", None)
    
    # Si la validación de seguridad falló, no ejecutamos y propagamos el error de validación
    if not query_valid:
        return {
            "sql_results": None,
            "execution_error": f"Ejecución cancelada por validación de seguridad: {validation_error}"
        }
        
    conn = get_db_connection()
    
    try:
        # Ejecutar la consulta y convertir el resultado a un DataFrame de Pandas
        # Luego a una lista de diccionarios para facilitar la serialización del estado
        res_df = conn.query(sql_query).df()
        
        # Formatear timestamps/fechas a string si es necesario para evitar problemas de serialización
        for col in res_df.columns:
            if res_df[col].dtype in ['datetime64[ns]', 'timestamp[ns]']:
                res_df[col] = res_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                
        results = res_df.to_dict(orient="records")
        
        return {
            "sql_results": results,
            "execution_error": None
        }
    except Exception as e:
        # Capturamos el error para alimentar el flujo de auto-corrección
        return {
            "sql_results": None,
            "execution_error": str(e)
        }
