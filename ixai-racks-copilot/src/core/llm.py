import os
import google.generativeai as genai
from groq import Groq
from src.core.config import Config

# Inicializar Gemini solo si la clave está disponible en tiempo de ejecución
_gemini_key = Config.get_gemini_api_key()
if _gemini_key:
    genai.configure(api_key=_gemini_key)

_groq_client = None
def get_groq_client():
    global _groq_client
    groq_key = Config.get_groq_api_key()
    if _groq_client is None and groq_key:
        _groq_client = Groq(api_key=groq_key)
    return _groq_client

def call_llm(prompt: str, system_instruction: str = None) -> str:
    """
    Realiza una llamada al LLM configurado (Gemini o Groq) y devuelve el texto de respuesta.
    """
    provider = Config.DEFAULT_LLM_PROVIDER

    if provider == "gemini":
        try:
            gemini_key = Config.get_gemini_api_key()
            if not gemini_key:
                raise ValueError("GEMINI_API_KEY no configurado")

            model_name = "gemini-2.5-flash"

            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
            else:
                model = genai.GenerativeModel(model_name=model_name)

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            if Config.get_groq_api_key():
                print(f"Fallo Gemini ({e}). Intentando fallback con Groq...")
                return call_groq(prompt, system_instruction)
            raise e
    else:
        return call_groq(prompt, system_instruction)

def call_groq(prompt: str, system_instruction: str = None) -> str:
    client = get_groq_client()
    if not client:
        raise ValueError("GROQ_API_KEY no configurado para usar Groq.")
        
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        temperature=0.1
    )
    return chat_completion.choices[0].message.content.strip()
