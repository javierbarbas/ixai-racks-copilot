from src.core.llm import call_llm

def route_intent(user_question: str) -> str:
    """
    Clasifica la intención de la pregunta del usuario utilizando LLM.
    Retorna: 'greeting', 'visualize', o 'query'.
    """
    system_instruction = (
        "Eres un clasificador de intenciones experto para el sistema IxAI Racks Copilot.\n"
        "Debes categorizar el mensaje del usuario en una de las siguientes opciones:\n"
        "- 'greeting': Si el usuario saluda, se despide, agradece, hace preguntas generales sobre la identidad del bot o pide ayuda general de qué puede hacer.\n"
        "- 'visualize': Si el usuario solicita explícitamente ver gráficos, visualizaciones, paneles, KPIs o abrir el dashboard visual.\n"
        "- 'query': Si el usuario realiza una pregunta analítica específica que requiere consultar la base de datos de producción de racks (ej. cantidades, fechas, operadores, lotes, eficiencia, turnos).\n"
        "REGLA: Responde ÚNICAMENTE con una de las palabras: 'greeting', 'visualize' o 'query'."
    )
    
    prompt = f"Categoriza la siguiente consulta del usuario: \"{user_question}\""
    
    try:
        response = call_llm(prompt=prompt, system_instruction=system_instruction)
        decision = response.lower().strip()
        # Sanitizar respuesta en caso de ruido
        if "greeting" in decision:
            return "greeting"
        elif "visualize" in decision:
            return "visualize"
        else:
            return "query"
    except Exception as e:
        print(f"Error en enrutador de intenciones: {e}. Defaulteando a 'query'.")
        return "query"
