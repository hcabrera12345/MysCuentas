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
        You are an intelligent expense assistant. Your job is to extract expense data from the user's text: "{text}"
        
        CRITICAL RULES:
        1. FLEXIBILITY: The order does NOT matter. "Gasolina 50" is the same as "50 Gasolina".
        2. CORRECTIONS: If the user corrects themselves, use the FINAL value. Ex: "50 bread, no, 60" -> amount: 60.
        3. MULTI-ITEM: If there are multiple distinct expenses, return a LIST of JSON objects. If only one, return a single object.
        
        Output RAW JSON (no markdown). 
        Keys: 
        - item: Short description (e.g., "Pan", "Taxi").
        - amount: Numeric value (e.g., 50.5).
        - currency: Default 'Bs' if not specified.
        - category: One of [{cat_str}]. INFER the best fit.
        - date: YYYY-MM-DD (only if explicitly mentioned, else null).
        """
        try:
            response = self.model.generate_content(prompt)
            if not response or not response.text:
                return {"error": "Empty response from AI"}
            
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error processing text: {error_msg}")
            return {"error": error_msg}

    def process_audio(self, audio_path: str, categories: list = None) -> dict:
        cat_str = ", ".join(categories) if categories else "Alimentos, Transporte, Hogar, Servicios, Entretenimiento, Salud, Otros"

        prompt = f"""
        Listen to this audio. It is a user describing expenses. Extract details into JSON.
        
        RULES:
        1. IGNORE WORD ORDER. "50 taxi" = "taxi 50".
        2. HANDLE SLANG: "Lucas", "Pesos", "Bolis" -> usually currency or ignorable if amount is clear.
        3. HEAR CORRECTIONS: "Gaste 100... mentira, fueron 120" -> Amount is 120.
        
        Return RAW JSON (no markdown). Keys: item, amount, currency (default Bs), category, date.
        Category MUST be one of: [{cat_str}].
        """
        try:
            # Use Inline Data
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "audio/ogg",
                    "data": audio_data
                }
            ])
            
            if not response or not response.text:
                return {"error": "Empty response from AI (Audio)"}
                
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
        
        RULES:
        1. REPORT: Any query about "gastos", "total", "cuanto", "dame", "ver", "necesito", "reporte".
           - Ex: "dame los gastos de hoy", "cuanto gaste en comida", "total transporte ayer", "necesito reporte".
           - "Quiero ver mis gastos" -> REPORT.
        
        2. DELETE: "borra", "elimina", "me equivoque", "deshacer".

        3. EXPENSE: ONLY if it implies *spending now* or *logging data*.
           - Ex: "50 pan", "gaste 10 taxi", "anota comida 20", "compré zapatos".
           - FLEXIBLE ORDER: "Gasolina 50" is EXPENSE. "50 Gasolina" is EXPENSE.
           - If ambiguous but contains "dame" or "ver", it is REPORT.

        Output RAW JSON (no markdown):
        {{
            "type": "EXPENSE" | "REPORT" | "DELETE",
            "data": {{ ... }}
        }}

        If EXPENSE, extract: item, amount, currency (default 'Bs'), category, date.
        
        If REPORT, extract: 
        - query_type ('total','list','graph')
        - category (optional)
        - time_range (today, week, month, year, or all)
        - filter_user (optional)
        - format (optional: 'text', 'table', 'graph') -> ONLY if user explicitly asks (e.g., "dame una tabla").
        
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
