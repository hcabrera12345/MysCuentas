import unittest
from unittest.mock import MagicMock, patch
import asyncio
from bot import process_input

class TestBot(unittest.TestCase):
    def setUp(self):
        # Mock handlers
        self.mock_ai = MagicMock()
        self.mock_sheets = MagicMock()
        
        # Patch them in bot module (need to patch where they are imported/used)
        # Since bot.py instantiates them globally, we'd need to mock the classes before import or patch instances.
        # For simplicity in this script, we will assume we can patch 'bot.ai_handler' and 'bot.sheets_handler'
        pass

    @patch('bot.ai_handler')
    @patch('bot.sheets_handler')
    async def test_process_expense_text(self, mock_sheets, mock_ai):
        # Setup Mock
        mock_ai.parse_intent.return_value = {
            "type": "EXPENSE",
            "data": {
                "item": "Gasolina",
                "amount": 50,
                "currency": "Bs",
                "category": "Transporte",
                "date": "2025-01-01"
            }
        }
        mock_sheets.add_expense.return_value = True
        
        # Mock Update object
        mock_update = MagicMock()
        mock_update.message.reply_text = MagicMock()
        # Async mock for reply
        future = asyncio.Future()
        future.set_result(MagicMock())
        mock_update.message.reply_text.return_value = future

        await process_input(mock_update, "Gasolina 50", is_voice=False)
        
        # Assertions
        mock_ai.parse_intent.assert_called_once()
        mock_sheets.add_expense.assert_called_with("2025-01-01", "Transporte", "Gasolina", 50, "Bs")

if __name__ == '__main__':
    # Running this requires proper mocking of top-level code in bot.py 
    # (specifically the initialization blocks). 
    # For now, this file serves as a logic check template.
    print("Test script created. Run with 'python -m unittest test_bot.py' after commenting out top-level checks in bot.py")
