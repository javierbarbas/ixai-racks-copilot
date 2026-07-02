import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Ruta por defecto
DEFAULT_EXCEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "produccion_racks.xlsx"
)

# Conexión global única (patrón Singleton simple para la sesión)
_conn = None

def get_db_connection() -> duckdb.DuckDBPyConnection:
    """
    Retorna la instancia global de conexión a DuckDB (in-memory).
    """
    global _conn
    if _conn is None:
        _conn = duckdb.connect(database=":memory:")
    return _conn

def init_db(excel_path: str = None) -> duckdb.DuckDBPyConnection:
    """
    Carga el archivo Excel en un DataFrame de Pandas y lo registra 
    como una vista/tabla en DuckDB bajo el nombre 'produccion_racks'.
    """
    if excel_path is None:
        excel_path = os.getenv("EXCEL_DATA_PATH", DEFAULT_EXCEL_PATH)
        
    # Validar que el archivo exista
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"No se encontró el archivo Excel de datos en: {excel_path}")
        
    # Leer el archivo Excel usando pandas + openpyxl
    df = pd.read_excel(excel_path, engine="openpyxl")
    
    # Obtener conexión y registrar DataFrame como tabla 'produccion_racks'
    conn = get_db_connection()
    conn.register("produccion_racks", df)
    
    return conn

def get_schema_info() -> str:
    """
    Retorna la descripción estructurada del esquema de la tabla 
    produccion_racks para inyectarla en el contexto del LLM.
    """
    conn = get_db_connection()
    try:
        # Consultar la información de columnas de DuckDB
        schema_df = conn.query("DESCRIBE produccion_racks").df()
        
        schema_lines = []
        schema_lines.append("Tabla: produccion_racks")
        schema_lines.append("Columnas:")
        for _, row in schema_df.iterrows():
            column_name = row['column_name']
            column_type = row['column_type']
            schema_lines.append(f" - {column_name} ({column_type})")
            
        # Añadir algunos ejemplos de valores para guiar al LLM
        schema_lines.append("\nEjemplo de datos (primer fila):")
        sample_df = conn.query("SELECT * FROM produccion_racks LIMIT 1").df()
        if not sample_df.empty:
            for col in sample_df.columns:
                schema_lines.append(f" - {col}: {sample_df.iloc[0][col]}")
                
        return "\n".join(schema_lines)
    except Exception as e:
        return f"Error obteniendo esquema: {str(e)}"

if __name__ == "__main__":
    print("--- Probando Conexión a DuckDB ---")
    try:
        conn = init_db()
        print("DuckDB conectado e inicializado en memoria con éxito.")
        
        # Realizar consulta de prueba
        res = conn.query("SELECT COUNT(*) as total_registros, SUM(cantidad_producida) as produccion_total FROM produccion_racks").df()
        print("\nResultado de consulta de prueba:")
        print(res.to_string(index=False))
        
        print("\nEsquema detectado:")
        print(get_schema_info())
    except Exception as e:
        print(f"Error durante la prueba de conexión: {e}")
