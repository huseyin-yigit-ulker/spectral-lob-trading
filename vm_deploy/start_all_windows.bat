@echo off
echo ========================================================
echo   TUM BOTLARI (V2 MINER + V5 SISTEMI) BASLATICI
echo ========================================================

echo [1/3] 100-Coin Veri Madencisi (V2) baslatiliyor...
start "V2 Multi Agent (100 Coin)" cmd /k ".\venv\Scripts\activate && python scripts\run_multi_agent.py"

echo [2/3] V5 Izci (Screener) arka planda baslatiliyor...
start "V5 Izci (Screener)" cmd /k ".\venv\Scripts\activate && python scripts\market_screener.py"

echo JSON dosyasinin olusmasi icin 5 saniye bekleniyor...
timeout /t 5 >nul

echo [3/3] V5 Tetikci (Dynamic SMC) baslatiliyor...
start "V5 Tetikci (Dynamic Agent)" cmd /k ".\venv\Scripts\activate && python scripts\run_dynamic_smc.py"

echo Tum sistemler basariyla baslatildi. 3 ayri pencereyi kucultebilirsiniz.
