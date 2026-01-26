import google.generativeai as genai
import os
import json

class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Try loading from parent .env if running locally nested
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            
        if not api_key:
            print("Warning: GEMINI_API_KEY not found.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name="gemini-flash-latest")

    def _clean_json(self, text: str):
        text = text.replace("```json", "").replace("```", "").strip()
        return text

    def parse_intent(self, text: str, categories: list = None) -> dict:
        cat_str = ", ".join(categories) if categories else "standard categories"

        prompt = f"""
        Analyze logic: Is input "{text}" a REPORT Request, an EXPENSE Log, or a DELETION Request?
        
        RULES:
        1. REPORT: Any query about "gastos", "total", "cuanto", "dame", "ver", "necesito", "reporte".
           - Ex: "dame los gastos de hoy", "cuanto gaste en comida", "total transporte ayer", "necesito reporte".
           - Even if it mentions categories ("alimentos"), it is a REPORT if it asks for "dame" or "cuanto".
        
        2. DELETE: "borra", "elimina", "me equivoque", "deshacer".

        3. EXPENSE: ONLY if it implies *spending now* or *logging data*.
           - Ex: "50 pan", "gaste 10 taxi", "anota comida 20", "compré zapatos".
           - If ambiguous but contains "dame" or "ver", it is REPORT.

        Output RAW JSON (no markdown):
        {{
            "type": "EXPENSE" | "REPORT" | "DELETE",
            "data": {{ ... }}
        }}

        If EXPENSE, extract: item, amount, currency (default 'Bs'), category, date.
        CRITICAL FOR CATEGORY: Match the input item to the BEST category from this list: [{cat_str}].

        If REPORT, extract: 
        - query_type ('total','list','graph')
        - category (optional, if mentioned like "gastos en alimentos")
        - time_range (today, week, month, year, or all)
        - filter_user (optional, if mentioned like "por Hernan")
        
        If DELETE, data is empty {{}}.
        """
        try:
            if not hasattr(self, 'model'):
                return {"error": "AI Model not initialized (missing key)"}
                
            response = self.model.generate_content(prompt)
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            return {"error": f"AI Parsing Error: {str(e)}"}
