echo "Arka planda calisan (Headless) tum Bot islemleri durduruluyor..."
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "scripts" } | Stop-Process -Force 2>$null
echo "Tum botlar basariyla durduruldu."
