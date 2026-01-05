import google.generativeai as genai
import os
import json
import typing_extensions as typing

class Expense(typing.TypedDict):
    item: str
    amount: float
    currency: str
    category: str
    date: str

class AIHandler:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        
        # verified working model via REST check: gemini-flash-latest
        self.model = genai.GenerativeModel(
            model_name="gemini-flash-latest" 
        )

    def _clean_json(self, text: str):
        # Remove markdown code blocks if present
        text = text.replace("```json", "").replace("```", "").strip()
        return text

    def process_text(self, text: str, categories: list = None) -> dict:
        cat_str = ", ".join(categories) if categories else "Alimentos, Transporte, Hogar, Servicios, Entretenimiento, Salud, Otros"
        
        prompt = f"""
        You are an expense tracking assistant. Extract expense details from this text: "{text}"
        
        It is almost certainly an expense log unless explicitly stated otherwise.
        Synonyms for expense: gasto, compra, pago, costo, anota, registras, etc.
        Also simple phrases like "50 bs en pan" are expenses.
        
        Return RAW JSON (no markdown formatting) with these keys:
        - item: What was bought (short description).
        - amount: The number (numeric).
        - currency: Currency symbol/code (default 'Bs' if not found).
        - category: One of [{cat_str}]. Infer best fit.
        - date: YYYY-MM-DD (only if explicitly mentioned, else null).
        """
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error processing text: {error_msg}")
            return {"error": error_msg}

    def process_audio(self, audio_path: str, categories: list = None) -> dict:
        cat_str = ", ".join(categories) if categories else "Alimentos, Transporte, Hogar, Servicios, Entretenimiento, Salud, Otros"

        prompt = f"""
        Listen to this audio. It is a user describing an expense. Extract details into JSON.
        Examples: "Compré pan 5 pesos", "Gasto de taxi 20", "Anota 50 en remeras".
        
        Return RAW JSON (no markdown) with keys: item, amount, currency (default Bs), category, date.
        Category MUST be one of: [{cat_str}].
        """
        try:
            # Use Inline Data (sending bytes directly) to avoid 'upload_file' errors on Render
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "audio/ogg",
                    "data": audio_data
                }
            ])
            
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error processing audio: {error_msg}")
            return {"error": error_msg}

    def parse_intent(self, text: str, categories: list = None) -> dict:
        """
        Determines if the user wants to log an expense, asks for a report, or wants to delete something.
        """
        cat_str = ", ".join(categories) if categories else "standard categories"

        prompt = f"""
        Analyze logic: Is input "{text}" a REPORT Request, an EXPENSE Log, or a DELETION Request?
        
        - DELETE: "borra el ultimo", "me equivoque", "elimina eso", "corrige", "deshacer".
        - REPORT: "dame reporte", "cuanto gaste?", "grafico", "resumen".
        - EXPENSE: spending money. "50 pan", "gaste 10", "comida 20", "anota 5".
        
        Output RAW JSON (no markdown):
        {{
            "type": "EXPENSE" | "REPORT" | "DELETE",
            "data": {{ ... }}
        }}

        If EXPENSE, extract: item, amount, currency (default 'Bs'), category, date.
        CRITICAL FOR CATEGORY: Match the input item to the BEST category from this list: [{cat_str}].
        - "Gasolina", "Taxi", "Bus" -> Transporte
        - "Cine", "Juego" -> Entretenimiento
        - "Remera", "Zapato" -> Ropa (if exists) or Otros

        If REPORT, extract: 
        - query_type ('total','list','graph')
        - category (optional, if specific category mentioned like "gasto en comida")
        - time_range (today, week, month, year, or all)
        - filter_user (optional, if a name is mentioned like "por Hernan" or "de Maria")
        
        If DELETE, data is empty {{}}.
        """
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error parsing intent: {error_msg}")
            return {"error": error_msg}
