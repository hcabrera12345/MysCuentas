import os
import google.generativeai as genai
import json
import logging
from dotenv import load_dotenv

# Load Env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.error("GEMINI_API_KEY missing!")

SYSTEM_PROMPT = """
You are an intelligent expense classifier for a personal finance bot (MysCuentas).
Extract expense details from the user's input (Text or Audio).
Return ONLY valid JSON. No Markdown. No comments.

JSON Structure:
{
    "amount": <number>,
    "currency": "<string: BOB or USD>",
    "category": "<string: Fijo or Variable>",
    "subcategory": "<string: best fit from list>",
    "description": "<string: brief summary>",
    "confidence": <float: 0.0 to 1.0>
}

Categories & Subcategories:
[FIJO]:
- Vivienda (Alquiler, Hipoteca, Mantenimiento)
- Servicios (Luz, Agua, Internet, Gas)
- Auto (Gasolina, Seguro, Mantenimiento)
- Educación (Colegiatura, Cursos)
- Seguros (Vida, Salud)
- Deudas (Préstamos, Tarjetas)

[VARIABLE]:
- Alimentación (Supermercado, Mercado)
- Comida Fuera (Restaurantes, Delivery, Snacks)
- Transporte Var (Taxi, Bus, Teleférico)
- Salud (Farmacia, Consultas)
- Cuidado Personal (Barbería, Cosméticos)
- Hogar (Limpieza, Decoración)
- Entretenimiento (Cine, Streaming, Salidas)
- Regalos
- Otros

Defaults:
- Currency: BOB (Bolivianos) unless specified.
- If not an expense, return "confidence": 0.0.
"""

def analyze_expense(input_path_or_text, mime_type="text/plain"):
    """
    Robust Gemini Analysis.
    SAFE MODE: No schemas, no complex objects. Just text -> JSON.
    """
    try:
        # Use valid model name
        model = genai.GenerativeModel("gemini-flash-latest")
        
        content = [SYSTEM_PROMPT]
        
        if mime_type.startswith("audio/"):
            logger.info(f"Uploading audio: {input_path_or_text}")
            audio_file = genai.upload_file(path=input_path_or_text, mime_type=mime_type)
            content.append(audio_file)
            content.append("Analyze this audio.")
        else:
            content.append(f"Input: {input_path_or_text}")

        # GENERATE
        logger.info("Sending request to Gemini...")
        response = model.generate_content(content)
        
        raw_text = response.text
        logger.info(f"Gemini Raw: {raw_text}")
        
        # CLEANUP & PARSE
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data

    except Exception as e:
        logger.error(f"Gemini Error: {e}", exc_info=True)
        return None
