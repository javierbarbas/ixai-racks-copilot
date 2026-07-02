import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data():
    np.random.seed(42)
    
    # Parámetros de simulación
    num_rows = 200
    start_date = datetime.now() - timedelta(days=60)
    
    # Modelos de rack
    modelos = [
        "Rack Industrial Pesado H1",
        "Rack Paletización Estándar P2",
        "Estantería Ligera L3",
        "Rack Cantilever C4"
    ]
    
    # Operadores y turnos
    operadores = ["Carlos Gomez", "Ana Martinez", "Luis Rodriguez", "Sofia Perez", "Jorge Hernandez"]
    turnos = ["Matutino", "Vespertino", "Nocturno"]
    
    data = []
    
    for i in range(num_rows):
        fecha = start_date + timedelta(days=np.random.randint(0, 60))
        # Formatear fecha sin horas para simplicidad
        fecha_str = fecha.strftime("%Y-%m-%d")
        
        lote_id = f"LOTE-{1000 + i}"
        modelo = np.random.choice(modelos)
        
        # Producción según tipo de rack
        if "Pesado" in modelo:
            cantidad_producida = int(np.random.normal(60, 10))
        elif "Estándar" in modelo:
            cantidad_producida = int(np.random.normal(120, 15))
        elif "Ligera" in modelo:
            cantidad_producida = int(np.random.normal(200, 25))
        else: # Cantilever
            cantidad_producida = int(np.random.normal(80, 12))
            
        cantidad_producida = max(10, cantidad_producida)
        
        # Defectuosos (un porcentaje pequeño, con variaciones por operador/turno)
        turno = np.random.choice(turnos)
        operador = np.random.choice(operadores)
        
        tasa_defecto_base = 0.03
        # El turno nocturno tiene ligeramente más defectos
        if turno == "Nocturno":
            tasa_defecto_base += 0.02
        # Algunos operadores son más experimentados
        if operador == "Carlos Gomez":
            tasa_defecto_base -= 0.01
            
        cantidad_defectuosa = int(cantidad_producida * max(0.005, np.random.normal(tasa_defecto_base, 0.01)))
        cantidad_defectuosa = max(0, min(cantidad_defectuosa, cantidad_producida - 5))
        
        # Eficiencia
        eficiencia = round(float(np.random.uniform(70.0, 99.0)), 2)
        
        data.append({
            "fecha": fecha_str,
            "lote": lote_id,
            "modelo_rack": modelo,
            "cantidad_producida": cantidad_producida,
            "cantidad_defectuosa": cantidad_defectuosa,
            "operador": operador,
            "turno": turno,
            "eficiencia_porcentaje": eficiencia
        })
        
    df = pd.DataFrame(data)
    
    # Ordenar por fecha
    df = df.sort_values(by="fecha").reset_index(drop=True)
    
    # Crear carpeta de datos si no existe
    os.makedirs("data", exist_ok=True)
    
    excel_path = "data/produccion_racks.xlsx"
    df.to_excel(excel_path, index=False, engine="openpyxl")
    print(f"Dataset simulado generado exitosamente en '{excel_path}' con {len(df)} registros.")

if __name__ == "__main__":
    generate_mock_data()
