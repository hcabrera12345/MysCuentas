from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.sheets_adapter import SheetsAdapter
from datetime import datetime

router = APIRouter(prefix="/finance", tags=["Finance Bot 💰"])
try:
    sheets = SheetsAdapter()
except Exception as e:
    print(f"Warning: SheetsAdapter failed to init: {e}")
    sheets = None

# Data Models
class ExpenseParam(BaseModel):
    item: str
    amount: float
    currency: str = "Bs"
    category: str = "Otros"
    user: str = "Unknown"
    date: str = None

@router.post("/expense")
async def log_expense(expense: ExpenseParam):
    """
    Logs a new expense to Google Sheets.
    """
    if not sheets:
        raise HTTPException(status_code=503, detail="Sheets Service Unavailable")
    
    date = expense.date or datetime.now().strftime("%Y-%m-%d")
    
    success = sheets.add_expense(
        date=date,
        category=expense.category,
        item=expense.item,
        amount=expense.amount,
        currency=expense.currency,
        user_name=expense.user
    )
    
    if success:
        return {"status": "success", "message": f"Expense '{expense.item}' logged for {expense.user}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to log to Sheets")

@router.get("/report")
async def get_report(user: str = None, time_range: str = "today"):
    """
    Get expense reports.
    """
    return {"status": "success", "report": f"Fake report for {user} ({time_range})"}
