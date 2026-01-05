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
        
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": Expense
            }
        )

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
            return json.loads(response.text)
        except Exception as e:
            print(f"Error processing text: {e}")
            return None

    def process_audio(self, audio_path: str) -> dict:
        prompt = """
        Listen to this audio and extract the expense details.
        
        Rules:
        - If no currency is specified, assume 'Bs'.
        - Categories should be one of: Alimentos, Transporte, Hogar, Servicios, Entretenimiento, Salud, Otros.
        - Date should be in YYYY-MM-DD format if mentioned, otherwise leave empty.
        """
        try:
            audio_file = genai.upload_file(audio_path)
            response = self.model.generate_content([prompt, audio_file])
            return json.loads(response.text)
        except Exception as e:
            print(f"Error processing audio: {e}")
            return None

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
            return json.loads(response.text)
        except Exception as e:
            print(f"Error parsing intent: {e}")
            return None
