import os
import requests
from dotenv import load_dotenv

load_dotenv()

import time

def send_telegram_message(text: str):
    """Telegram uzerinden HTML formatinda guvenli bildirim gonderir (Retry & Fallback korumali)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    for attempt in range(2):
        try:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            r = requests.post(url, json=payload, timeout=8)
            if r.ok:
                return
            
            # Eger HTML parse hatasi alindiysa, HTML taglerini kaldirip duz metin olarak ilet
            if "can't parse entities" in r.text or r.status_code == 400:
                clean_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
                r_fallback = requests.post(url, json={"chat_id": chat_id, "text": clean_text}, timeout=8)
                if r_fallback.ok:
                    return
            
            time.sleep(1)
        except Exception as e:
            time.sleep(1)
            continue
