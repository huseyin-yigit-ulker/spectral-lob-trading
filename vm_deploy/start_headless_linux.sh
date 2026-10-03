#!/bin/bash
# Hangi klasorden calistirilirsa calistirilsin, projenin ana dizinine (bir ust klasore) gec:
cd "$(dirname "$0")/.." || exit

echo "Eski botlar temizleniyor..."
pkill -f "python scripts/" 2>/dev/null
pkill -f "python3 scripts/" 2>/dev/null

mkdir -p logs

PYTHON_CMD="python3"
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f "venv/Scripts/python" ]; then
    PYTHON_CMD="venv/Scripts/python"
fi

echo "Secilen Python Yolu: $PYTHON_CMD"


echo "1) V5 Izci (Screener) arka planda baslatiliyor..."
nohup $PYTHON_CMD -u scripts/market_screener.py > logs/nohup_screener.log 2>&1 &

sleep 5

echo "2) V5 Tetikci (SMC) arka planda baslatiliyor..."
nohup $PYTHON_CMD -u scripts/run_dynamic_smc.py > logs/nohup_dynamic_smc.log 2>&1 &

echo "--------------------------------------------------------"
echo "TUM BOTLAR GORUNMEZ (NOHUP) MODDA BASLATILDI!"
echo "Botlarin ne yaptigini izlemek icin: tail -f logs/nohup_dynamic_smc.log"
