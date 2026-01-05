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
        
        # Switched to gemini-1.5-flash to avoid Free Tier Quota (429) errors on 2.0
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash" 
        )

    def _clean_json(self, text: str):
        # Remove markdown code blocks if present
        text = text.replace("```json", "").replace("```", "").strip()
        return text

    def process_text(self, text: str) -> dict:
        prompt = f"""
        Extract the expense details from the following text:
        "{text}"
        
        Rules:
        - If no currency is specified, assume 'Bs'.
        - Categories should be one of: Alimentos, Transporte, Hogar, Servicios, Entretenimiento, Salud, Otros.
        - Date should be in YYYY-MM-DD format if mentioned, otherwise leave empty.
        """
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error processing text: {error_msg}")
            return {"error": error_msg}

    def process_audio(self, audio_path: str) -> dict:
        prompt = "Listen to this audio and extract expense details. Return ONLY JSON."
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

    def parse_intent(self, text: str) -> dict:
        """
        Determines if the user wants to log an expense or asks for a report.
        Returns JSON with 'type': 'EXPENSE' | 'REPORT' and relevant data.
        """
        prompt = f"""
        Analyze the following user input and determine if it is an Expense Log or a Report Request.
        Input: "{text}"
        
        Output JSON schema:
        {{
            "type": "EXPENSE" or "REPORT",
            "data": {{ ... }}
        }}

        If EXPENSE, "data" should contain:
        - item: str
        - amount: float
        - currency: str (default 'Bs')
        - category: str (Alimentos, Transporte, Hogar, Servicios, Entretenimiento, Salud, Otros)
        - date: str (YYYY-MM-DD or null)

        If REPORT, "data" should contain:
        - query_type: "total" | "list" | "graph"
        - category: str (optional filter)
        - time_range: "today" | "week" | "month" | "all" (infer from context)
        """
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = self._clean_json(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error parsing intent: {error_msg}")
            return {"error": error_msg}
