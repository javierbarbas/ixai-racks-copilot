---
title: IxAI Racks Copilot
emoji: 📦
colorFrom: blue
colorTo: indigo
sdk: streamlit
app_file: main.py
pinned: false
---

# IxAI Racks Copilot

Dashboard operativo de produccion de racks con:
- Resumen Ejecutivo
- Operacion Semanal
- Detalle por PO / Planeador
- Copiloto conversacional (Groq)

## Ejecutar local

```bash
pip install -r requirements.txt
streamlit run main.py
```

## Despliegue en Hugging Face Spaces

1. Crea un Space nuevo con SDK `Streamlit`.
2. Sube el contenido de este directorio (`ixai-racks-copilot/`) al Space.
3. En `Settings -> Secrets`, agrega:
   - `GROQ_API_KEY`
4. Reinicia el Space.

## Notas de datos

- El app usa `data/warehouse.duckdb`.
- Si no existe en primer arranque, se genera automaticamente ejecutando `etl/ingest.py` usando `data/data_produccion.xlsx`.
- Asegurate de incluir `data/data_produccion.xlsx` en el repo del Space.

## Variables opcionales

- `GROQ_API_KEY`: habilita el chat conversacional.
