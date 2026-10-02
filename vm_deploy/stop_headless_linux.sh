#!/bin/bash
echo "Arka planda calisan tum Python (Bot) islemleri durduruluyor..."
pkill -f "python scripts/" 2>/dev/null
pkill -f "python3 scripts/" 2>/dev/null
echo "Tum botlar basariyla durduruldu."
