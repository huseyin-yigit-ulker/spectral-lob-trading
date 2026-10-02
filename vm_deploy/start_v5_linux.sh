# Linux/Ubuntu tmux baslatma scripti
#!/bin/bash
echo "Eski V5 oturumlari kapatiliyor..."
tmux kill-session -t v5_bot 2>/dev/null

echo "Yeni V5 tmux oturumu baslatiliyor..."
tmux new-session -d -s v5_bot

# Sol panel: Screener
tmux send-keys -t v5_bot "source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null" C-m
tmux send-keys -t v5_bot "python scripts/market_screener.py" C-m

# Sag panel: Agent
tmux split-window -h -t v5_bot
tmux send-keys -t v5_bot "source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null" C-m
tmux send-keys -t v5_bot "sleep 5 && python scripts/run_dynamic_smc.py" C-m

echo "=========================================================="
echo " ?? V5 Dinamik SMC + Screener VM'de Basarila Baslatildi!"
echo "=========================================================="
echo "Botun ekranini (Canli Tabloyu) gormek icin su komutu yazin:"
echo "tmux attach -t v5_bot"
echo "Ekrandan cikmak (ama botu acik birakmak) icin: CTRL+B basip ardindan D tusuna basin."
