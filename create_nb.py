import json
import os

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 📊 Binance Futures - HFT Veri Analizi\n",
            "Bu notebook, ajanın topladığı `depth20@100ms` ve `aggTrade` verilerini incelemek, SMC (Smart Money Concepts) ve mikro-yapı metriklerini (OBI, CVD) görselleştirmek için hazırlanmıştır."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "import os\n",
            "from pathlib import Path\n",
            "\n",
            "# Grafik ayarları (Koyu tema)\n",
            "plt.style.use('dark_background')\n",
            "plt.rcParams['figure.figsize'] = (15, 6)\n",
            "plt.rcParams['axes.grid'] = True\n",
            "plt.rcParams['grid.alpha'] = 0.2"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "## 1. Verileri Yükleme\n",
            "data_dir = Path('../data')\n",
            "\n",
            "depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith('depth')])\n",
            "trade_files = sorted([f for f in os.listdir(data_dir) if f.startswith('trades')])\n",
            "\n",
            "if depth_files and trade_files:\n",
            "    # En son kaydedilen dosyaları al\n",
            "    df_depth = pd.read_parquet(data_dir / depth_files[-1])\n",
            "    df_trades = pd.read_parquet(data_dir / trade_files[-1])\n",
            "    \n",
            "    # Unix timestamp'leri Datetime'a çevir\n",
            "    df_depth['datetime'] = pd.to_datetime(df_depth['timestamp'], unit='ms')\n",
            "    df_trades['datetime'] = pd.to_datetime(df_trades['timestamp'], unit='ms')\n",
            "    \n",
            "    print(f'✅ Depth Verisi: {df_depth.shape[0]} satır yüklendi.')\n",
            "    print(f'✅ Trade Verisi: {df_trades.shape[0]} satır yüklendi.')\n",
            "else:\n",
            "    print('❌ Veri bulunamadı. Lütfen önce collect_data.py betiğini çalıştırın.')"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "## 2. Mid Price (Orta Fiyat) Çizimi\n",
            "# Mid Price = (En İyi Alış + En İyi Satış) / 2\n",
            "df_depth['mid_price'] = (df_depth['bid_price_0'] + df_depth['ask_price_0']) / 2\n",
            "\n",
            "plt.plot(df_depth['datetime'], df_depth['mid_price'], color='cyan', linewidth=1.5)\n",
            "plt.title('BTCUSDT - Fiyat Grafiği (Mid Price)', fontsize=14)\n",
            "plt.xlabel('Zaman')\n",
            "plt.ylabel('Fiyat (USDT)')\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "## 3. Order Book Imbalance (OBI) - Emir Defteri Dengesizliği\n",
            "# OBI, Alış baskısı ile Satış baskısı arasındaki orantısızlığı ölçer. (+1 tam alış, -1 tam satış)\n",
            "# İlk 5 kademe (Top 5 Levels) baz alınarak hesaplanır.\n",
            "\n",
            "bid_vols = sum(df_depth[f'bid_qty_{i}'] for i in range(5))\n",
            "ask_vols = sum(df_depth[f'ask_qty_{i}'] for i in range(5))\n",
            "\n",
            "df_depth['OBI'] = (bid_vols - ask_vols) / (bid_vols + ask_vols)\n",
            "\n",
            "fig, ax1 = plt.subplots(figsize=(15, 6))\n",
            "\n",
            "# Fiyat (Sol eksen)\n",
            "ax1.plot(df_depth['datetime'], df_depth['mid_price'], color='cyan', label='Fiyat')\n",
            "ax1.set_ylabel('Fiyat', color='cyan')\n",
            "ax1.tick_params(axis='y', labelcolor='cyan')\n",
            "\n",
            "# OBI (Sağ eksen)\n",
            "ax2 = ax1.twinx()\n",
            "ax2.plot(df_depth['datetime'], df_depth['OBI'], color='orange', alpha=0.5, label='OBI')\n",
            "ax2.set_ylabel('Imbalance (-1 to +1)', color='orange')\n",
            "ax2.axhline(0, color='white', linestyle='--', alpha=0.5)\n",
            "ax2.tick_params(axis='y', labelcolor='orange')\n",
            "ax2.set_ylim(-1.1, 1.1)\n",
            "\n",
            "plt.title('Fiyat Hareketi vs. Order Book Imbalance (İlk 5 Kademe)', fontsize=14)\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "## 4. Cumulative Volume Delta (CVD) - Kümülatif Hacim Deltası\n",
            "# Piyasa (Taker) alıcıları ile piyasa (Taker) satıcıları arasındaki net hacim farkı\n",
            "# is_buyer_maker == True -> İşlemi tetikleyen (Taker) satıcıdır, Maker alıcıdır (- Hacim)\n",
            "# is_buyer_maker == False -> İşlemi tetikleyen (Taker) alıcıdır, Maker satıcıdır (+ Hacim)\n",
            "\n",
            "df_trades['trade_side_vol'] = np.where(df_trades['is_buyer_maker'], -df_trades['quantity'], df_trades['quantity'])\n",
            "df_trades['CVD'] = df_trades['trade_side_vol'].cumsum()\n",
            "\n",
            "fig, ax1 = plt.subplots(figsize=(15, 6))\n",
            "\n",
            "# Fiyat (Sol eksen)\n",
            "ax1.plot(df_trades['datetime'], df_trades['price'], color='cyan', label='Fiyat')\n",
            "ax1.set_ylabel('Fiyat', color='cyan')\n",
            "ax1.tick_params(axis='y', labelcolor='cyan')\n",
            "\n",
            "# CVD (Sağ eksen)\n",
            "ax2 = ax1.twinx()\n",
            "ax2.plot(df_trades['datetime'], df_trades['CVD'], color='magenta', linewidth=2, label='CVD')\n",
            "ax2.set_ylabel('Net Hacim Farkı (BTC)', color='magenta')\n",
            "ax2.tick_params(axis='y', labelcolor='magenta')\n",
            "\n",
            "plt.title('Fiyat Hareketi vs. Cumulative Volume Delta (CVD)', fontsize=14)\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "## 5. Sipariş Defteri Derinlik Analizi (Anlık Snapshot)\n",
            "# Son snapshot üzerinden Alış (Bid) ve Satış (Ask) likiditesini görselleştirme\n",
            "\n",
            "last_row = df_depth.iloc[-1]\n",
            "\n",
            "bids_price = [last_row[f'bid_price_{i}'] for i in range(20)]\n",
            "bids_qty = [last_row[f'bid_qty_{i}'] for i in range(20)]\n",
            "\n",
            "asks_price = [last_row[f'ask_price_{i}'] for i in range(20)]\n",
            "asks_qty = [last_row[f'ask_qty_{i}'] for i in range(20)]\n",
            "\n",
            "plt.figure(figsize=(15, 6))\n",
            "plt.bar(bids_price, bids_qty, color='green', alpha=0.7, width=0.5, label='Alış (Bids)')\n",
            "plt.bar(asks_price, asks_qty, color='red', alpha=0.7, width=0.5, label='Satış (Asks)')\n",
            "plt.axvline(last_row['mid_price'], color='cyan', linestyle='--', label=f\"Mid Price: {last_row['mid_price']}\")\n",
            "\n",
            "plt.title('Derinlik Grafiği (Son Snapshot)', fontsize=14)\n",
            "plt.xlabel('Fiyat')\n",
            "plt.ylabel('BTC Miktarı (Likidite)')\n",
            "plt.legend()\n",
            "plt.show()"
        ]
    }
]

notebook = {
    "cells": cells,
    "metadata": {
        "language_info": {
            "name": "python",
            "version": "3.11"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

os.makedirs('notebooks', exist_ok=True)
with open('notebooks/data_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)
