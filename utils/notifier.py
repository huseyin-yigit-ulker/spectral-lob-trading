import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_telegram_message(text: str):
    """Telegram uzerinden HTML formatinda bildirim gonderir."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        # Sessizce don, botun calismasini engelleme
        return
        
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"  [Telegram Hatasi] {r.text[:150]}")
    except Exception as e:
        print(f"  [Telegram Exception] {e}")
