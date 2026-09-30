import asyncio
import websockets
import json

async def test():
    url = "wss://fstream.binance.com/stream?streams=btcusdt@depth20@100ms/btcusdt@aggTrade/btcusdt@trade/btcusdt@ticker"
    print(f"Baglanilan URL: {url}", flush=True)
    try:
        async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
            print("Baglanti basarili. Mesajlar bekleniyor...", flush=True)
            for i in range(20):
                msg = await ws.recv()
                data = json.loads(msg)
                stream = data.get("stream", "Bilinmeyen Stream")
                print(f"Gelen Paket: {stream}", flush=True)
    except Exception as e:
        print(f"Hata: {e}", flush=True)

asyncio.run(test())
