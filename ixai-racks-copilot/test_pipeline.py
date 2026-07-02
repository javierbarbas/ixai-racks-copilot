import os
from dotenv import load_dotenv
from src.db.connection import init_db, get_schema_info
from src.workflows.text_to_sql_flow import get_text_to_sql_graph

def run_test():
    load_dotenv()
    
    print("--- 1. Inicializando Conexión DuckDB ---")
    try:
        init_db()
        print("DuckDB cargado e inicializado correctamente.")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        return
        
    print("\n--- 2. Esquema de Base de Datos Detectado ---")
    print(get_schema_info())
    
    print("\n--- 3. Inicializando Flujo de Agente (LangGraph) ---")
    try:
        app = get_text_to_sql_graph()
        print("Grafo de LangGraph compilado exitosamente.")
    except Exception as e:
        print(f"Error al compilar el grafo: {e}")
        return
        
    # Pregunta de prueba
    test_question = "¿Cuántos racks se produjeron en total y cuántos salieron defectuosos?"
    print(f"\n--- 4. Ejecutando consulta de prueba: '{test_question}' ---")
    
    initial_state = {
        "user_question": test_question,
        "routing_decision": "query",
        "sql_query": None,
        "query_valid": False,
        "validation_error": None,
        "sql_results": None,
        "execution_error": None,
        "natural_response": None,
        "attempt_count": 0,
        "schema_info": None
    }
    
    # Validar API keys de LLM
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    if not gemini_key and not groq_key:
        print("\n[WARNING] No se encontraron API keys configuradas en el archivo .env.")
        print("Agregando una clave ficticia para validar sintaxis de importación y carga, pero la llamada de LLM fallará.")
        # Podemos omitir la ejecución real si no hay claves
        return
        
    try:
        result = app.invoke(initial_state)
        print("\n--- 5. Resultado del Grafo de Estado ---")
        print(f"SQL Generado: {result.get('sql_query')}")
        print(f"Es Válido por Seguridad: {result.get('query_valid')}")
        print(f"Resultados de Base de Datos (primeros 3): {result.get('sql_results')[:3] if result.get('sql_results') else None}")
        print(f"Intentos realizados: {result.get('attempt_count')}")
        print("\nRespuesta en Lenguaje Natural:")
        print(result.get("natural_response"))
    except Exception as e:
        print(f"\nError durante la ejecución del grafo: {e}")

if __name__ == "__main__":
    run_test()
