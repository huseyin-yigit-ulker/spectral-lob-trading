echo "Eski botlar temizleniyor..."
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "scripts" } | Stop-Process -Force 2>$null

echo "1) 100-Coin Madencisi (V2) arka planda baslatiliyor..."

echo "2) V5 Izci (Screener) arka planda baslatiliyor..."
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "scripts\market_screener.py" -WindowStyle Hidden -RedirectStandardOutput "logs\screener_console.log" -RedirectStandardError "logs\screener_error.log"

Start-Sleep -Seconds 5

echo "3) V5 Tetikci (SMC) arka planda baslatiliyor..."
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "scripts\run_dynamic_smc.py" -WindowStyle Hidden -RedirectStandardOutput "logs\dynamic_smc_console.log" -RedirectStandardError "logs\dynamic_smc_error.log"

echo "--------------------------------------------------------"
echo "TUM BOTLAR GORUNMEZ (HEADLESS) MODDA BASLATILDI!"
echo "Su an VS Code'u veya terminali kapatsaniz bile arka planda calismaya (log yazmaya) devam edecekler."
echo "Ekrana basilan tablo yazilari artik 'logs/dynamic_smc_console.log' dosyasina yazilmaktadir."
echo "Botlari durdurmak icin 'stop_headless.ps1' dosyasini calistirin."
