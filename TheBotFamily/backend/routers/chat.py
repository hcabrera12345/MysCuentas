from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import AIService
from services.sheets_adapter import SheetsAdapter
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["Natural Language Chat 💬"])

# Init Services
try:
    ai = AIService()
    sheets = SheetsAdapter()
except Exception as e:
    print(f"Service Init Error: {e}")
    ai = None
    sheets = None

class ChatMessage(BaseModel):
    text: str
    user: str = "Unknown"

@router.post("/")
async def chat_endpoint(message: ChatMessage):
    if not ai or not sheets:
        return {"response": "⚠️ Error: Cerebro desconectado (Servicios no iniciados)."}

    # 1. Get Categories for Context
    categories = sheets.get_categories()

    # 2. Parse Intent
    intent = ai.parse_intent(message.text, categories)
    
    intent_type = intent.get("type")
    data = intent.get("data", {})
    
    response_text = "🤷‍♂️ No entendí."

    # 3. Handle Intent
    if intent_type == "EXPENSE":
        # Log Expense
        success = sheets.add_expense(
            date=data.get("date") or datetime.now().strftime("%Y-%m-%d"),
            category=data.get("category", "Otros"),
            item=data.get("item", "Desconocido"),
            amount=data.get("amount", 0),
            currency=data.get("currency", "Bs"),
            user_name=message.user
        )
        if success:
            response_text = f"✅ Anotado: {data.get('item')} ({data.get('amount')}) en {data.get('category')}."
        else:
            response_text = "❌ Error guardando en la hoja."

    elif intent_type == "DELETE":
        deleted = sheets.delete_last_entry(message.user)
        if deleted:
            response_text = f"🗑️ Borrado último: {deleted}"
        else:
            response_text = "⚠️ No encontré nada reciente tuyo para borrar."

    elif intent_type == "REPORT":
        # TBD: Implement Report logic here using ReportEngine logic
        # For now simple ack
        response_text = f"📊 Buscando reporte... (Tipo: {data.get('query_type')})"
        # TODO: Integrate Report Engine
    
    return {
        "response": response_text,
        "intent": intent_type,
        "data": data
    }
