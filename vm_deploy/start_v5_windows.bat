@echo off
echo ========================================================
echo   V5 DINAMIK SMC VE SCREENER VM BASLATICI (WINDOWS)
echo ========================================================

echo [1/2] Izci (Screener) arka planda baslatiliyor...
start "V5 Izci (Screener)" cmd /k ".\venv\Scripts\activate && python scripts\market_screener.py"

echo JSON dosyasinin olusmasi icin 5 saniye bekleniyor...
timeout /t 5 >nul

echo [2/2] Tetikci (Dynamic SMC) baslatiliyor...
start "V5 Tetikci (Dynamic Agent)" cmd /k ".\venv\Scripts\activate && python scripts\run_dynamic_smc.py"

echo Her iki bot da basariyla baslatildi. Pencereleri kucultebilirsiniz.
