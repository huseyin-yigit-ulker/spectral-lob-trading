#!/bin/bash
echo "Eski botlar temizleniyor..."
pkill -f "python scripts/run_multi_agent.py" 2>/dev/null
pkill -f "python scripts/market_screener.py" 2>/dev/null
pkill -f "python scripts/run_dynamic_smc.py" 2>/dev/null

# Log klasorunun varligindan emin olalim
mkdir -p logs

echo "1) 100-Coin Madencisi (V2) arka planda baslatiliyor..."
nohup venv/bin/python scripts/run_multi_agent.py > logs/nohup_multi_agent.log 2>&1 &

echo "2) V5 Izci (Screener) arka planda baslatiliyor..."
nohup venv/bin/python scripts/market_screener.py > logs/nohup_screener.log 2>&1 &

sleep 5

echo "3) V5 Tetikci (SMC) arka planda baslatiliyor..."
nohup venv/bin/python scripts/run_dynamic_smc.py > logs/nohup_dynamic_smc.log 2>&1 &

echo "--------------------------------------------------------"
echo "TUM BOTLAR GORUNMEZ (NOHUP) MODDA BASLATILDI!"
echo "Su an SSH baglantisini veya VS Code'u kapatsaniz bile calismaya devam edecekler."
echo "Botun ne yaptigini canli izlemek icin su komutu yazabilirsiniz:"
echo "tail -f logs/nohup_dynamic_smc.log"
