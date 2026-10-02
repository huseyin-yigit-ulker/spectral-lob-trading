#!/bin/bash
echo "Eski oturumlar kapatiliyor..."
tmux kill-session -t crypto_bots 2>/dev/null

echo "100-Coinlik Veri Madencisi (V2) baslatiliyor..."
tmux new-session -d -s crypto_bots -n "V2_Miner"
tmux send-keys -t crypto_bots:0 "source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null" C-m
tmux send-keys -t crypto_bots:0 "python scripts/run_multi_agent.py" C-m

echo "V5 Sistemi (Screener + Agent) baslatiliyor..."
tmux new-window -t crypto_bots -n "V5_System"
tmux send-keys -t crypto_bots:1 "source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null" C-m
tmux send-keys -t crypto_bots:1 "python scripts/market_screener.py" C-m

tmux split-window -h -t crypto_bots:1
tmux send-keys -t crypto_bots:1 "source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null" C-m
tmux send-keys -t crypto_bots:1 "sleep 5 && python scripts/run_dynamic_smc.py" C-m

echo "=========================================================="
echo " ?? TUM BOTLAR (100 Coin + V5 Screener + V5 SMC) BASLATILDI!"
echo "=========================================================="
echo "Botlarin ekranini gormek icin su komutu yazin:"
echo "tmux attach -t crypto_bots"
echo "Acilan ekranda alt pencereler arasinda (V2 Miner ve V5 Sistemi) gecis yapmak icin: CTRL+B basip ardindan N veya P tuslarina basin."
