import datetime

def get_current_date():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

def format_currency(amount):
    return f"{amount:.2f}"
