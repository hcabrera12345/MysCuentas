import sys
import os

# Fix Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from MysCuentas.src.brain import analyze_expense

if __name__ == "__main__":
    print("Testing Gemini Brain...")
    
    # Text Test
    res = analyze_expense("Pagué 50 bs por el taxi")
    print(f"Result: {res}")
    
    if res and res.get('amount') == 50 and res.get('category') == 'Variable':
        print("SUCCESS: Text Analysis")
    else:
        print("FAILURE: Text Analysis")
