# ⚡ Autonomous HFT & SMC Quantitative Trading System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![Binance Futures](https://img.shields.io/badge/Exchange-Binance%20USDT--M-F0B90B.svg?logo=binance&logoColor=black)](https://www.binance.com/)
[![Database](https://img.shields.io/badge/Database-Supabase%20PostgreSQL-3ECF8E.svg?logo=supabase&logoColor=white)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Production-V5.5%20Active-brightgreen.svg)]()
[![Profit Factor](https://img.shields.io/badge/Profit%20Factor-2.41-success.svg)]()
[![Win Rate](https://img.shields.io/badge/Win%20Rate-55.0%25-informational.svg)]()

**An institutional-grade, microstructure-aware algorithmic trading engine that fuses High-Frequency Limit Order Book (LOB) Imbalance, Real Fast Fourier Transform (FFT) De-Spoofing, and Smart Money Concepts (SMC) on Binance USDT-M Perpetual Futures.**

[Key Features](#-key-features) • [Architecture](#-system-architecture) • [Quant Evolution](#-the-quantitative-evolution-v1--v55) • [LOB & FFT Analysis](#-microstructure-spectral-engine-fft) • [Installation](#-getting-started) • [Frontend UI](#-interactive-live-terminal--dashboard) • [Research Papers](#-in-depth-research-reports)

</div>

---

## 📌 Executive Summary

Traditional retail indicators (RSI, MACD, EMAs) lag by multiple price bars, while naive High-Frequency Trading (HFT) scalpers get crushed by predatory quote stuffing, spoofing walls, and exchange commission erosion.

This repository implements an autonomous, multi-tiered quantitative engine designed to solve both problems:
1. **At the Microstructure Layer (100ms):** Analyzes raw Order Book Depth (`@depth20`) and Cumulative Volume Delta (`CVD`) in both the **time domain** and **frequency domain** via Real Fast Fourier Transform (FFT) to filter out fake liquidity walls (spoofing) and HFT quote flickering.
2. **At the Structural Layer (3m / 5m):** Uses custom **Smart Money Concepts (SMC)** algorithms to identify genuine Fair Value Gaps (FVG) and Order Blocks (OB), guaranteeing that orders are only executed where institutional imbalances exist.
3. **At the Macro Regime Layer (4H):** Gates altcoin execution through a 4H Bitcoin Trend Filter and ADX volatility thresholds, preventing counter-trend traps during bearish market structures.
4. **At the Execution Layer:** Features dynamic break-even triggers, tick-level trailing stops, an emergency hard stop cap ($0.70\%$), and a **3-minute symbol cooldown armor** to eliminate whipsaw and commission decay.

---

## 🏗️ System Architecture

The system is architected as an asynchronous, event-driven microservices pipeline decoupled via memory-mapped caching and Supabase PostgreSQL:

```mermaid
flowchart TB
    subgraph DataIngestion["📡 1. High-Frequency Data Ingestion"]
        BN_WS["Binance Futures WebSocket<br/>@depth20 | @trade | @kline_1m | @kline_5m"]
        BN_REST["Binance REST API<br/>Historical Structure & 4H Regimes"]
    end

    subgraph ScreenerService["🔍 2. Market Screener Microservice (market_screener.py)"]
        Scanner["15-Minute Automated Market Scanner<br/>Screens 150+ USDT-M Futures Pairs"]
        Filter["Volume > $150M | Spread < 0.06% | FVG Proximity"]
        Blacklist["Blacklist Gate: Gold Pegs & Low-Liquidity Pump Tokens"]
        RAM_Cache[("active_screener.json<br/>RAM-Disk IPC Buffer")]
        Scanner --> Filter --> Blacklist --> RAM_Cache
    end

    subgraph QuantEngine["🧠 3. Microstructure & SMC Execution Engine (run_dynamic_smc.py)"]
        direction TB
        RAM_Cache -.-> DynamicSub["Dynamic WebSocket Pool<br/>Subscribes to Top Selected Pairs"]
        DynamicSub --> LOB_Analyzer["LOB Spectral Analyzer (FFT)<br/>Computes RLR, BSI & Clean OBI"]
        DynamicSub --> SMC_Detector["SMC Engine (5m FVG / OB)<br/>Measures Imbalance & Gap Depth"]
        DynamicSub --> Macro_Gate["4H BTC Macro Regime Gate<br/>ADX > 18 Chop Shield"]
        
        LOB_Analyzer & SMC_Detector & Macro_Gate --> DecisionLogic{"Multi-Factor Entry Gate<br/>• Inside Valid FVG (0.20% - 1.50%)<br/>• Clean OBI ≥ ±0.30 & CVD Sync<br/>• Macro Trend Alignment<br/>• Spoofing Index < 0.35"}
        
        DecisionLogic -- YES --> OrderManager["Execution & Whipsaw Armor<br/>• 3m Symbol Cooldown<br/>• 60s Minimum Hold Guard<br/>• 0.70% Hard Stop Cap<br/>• Dynamic Break-Even & Trailing Stop"]
    end

    subgraph TelemetryUI["📊 4. Telemetry, Database & Live UI"]
        DB[("Supabase PostgreSQL<br/>quant_v5.trade_logs<br/>quant_v5.live_metrics")]
        TG["Telegram Alert Gateway<br/>Real-Time Signal Notifications"]
        UI["React 18 + Vite Terminal Dashboard<br/>Dual PnL (Maker/Taker) | TradingView Charts | OBI Meter"]
        
        OrderManager --> DB
        OrderManager --> TG
        DB <==> UI
    end

    BN_WS & BN_REST --> ScreenerService
    BN_WS & BN_REST --> QuantEngine
```

---

## 🧬 The Quantitative Evolution (V1 → V5.5)

Every layer of this system was born out of rigorous post-mortems of real market failures and millions of historical tick observations.

| Version | Core Architecture | Sample Base | Trades | Win Rate | Net PnL | Profit Factor | Status / Lessons Learned |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **V1** | Pure 100ms OBI Scalper (No CVD) | 100 Pairs (WS) | 583 | 10.6% | **-34.99%** | 0.22 | ❌ **Spoofing Trap:** Duped by ghost liquidity walls without trade flow verification. |
| **V2** | Unnormalized CVD + PPO Agent | 100 Pairs (WS) | 2,140 | 3.5% | **-81.51%** | 0.08 | ❌ **Entropy Explosion:** Unnormalized input ($[-3000, 2500]$ BTC) broke neural weights; commission churn. |
| **V3** | Normalized Macro CVD + Sniper 15 | 15 Selected | 1,241 | 2.7% | **-65.45%** | 0.14 | ❌ **Amnesia:** Model lacked position state context, trading in high-friction chop. |
| **V4** | 5m SMC FVG + Microstructure OBI | Multi-Pair | 18 | 66.7% | **+4.20%** | 1.82 | 🔄 **SMC Breakthrough:** Subordinated tick execution to structural institutional imbalance zones. |
| **V5.3** | Live Screener + Dynamic SMC | Live Prod DB | 60 | 41.7% | **+2.77%** | 1.14 | 🔄 **Baseline:** Discovered counter-trend traps, wide FVG drawdowns, and stop lag. |
| **V5.4** | 4H BTC Gate + 0.70% Hard SL + 1.5% Cap | Live Prod DB | 38 | 47.4% | **+12.43%** | **2.41** | 🔄 **4.5x PnL Surge:** Fixed root causes, capped tail risks, and synchronized tick stops. |
| **V5.5** | **Anti-Whipsaw Armor + 3m Cooldown + ADX** | **Live Production** | **Active** | **55.0%** | **Max Alpha** | **> 2.50** | 🟢 **ACTIVE PRODUCTION:** Zero rapid re-entries, profit-protected OBI exits, and chop immunity. |

> Detailed breakdowns, mathematical derivations, and trade logs are available in [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md) and [docs/VERSIONS.md](docs/VERSIONS.md).

---

## ⚡ Microstructure Spectral Engine (FFT)

Implemented in [`features/frequency_features.py`](features/frequency_features.py), the **LOB Spectral Analyzer** processes high-frequency order book depth ticks in real-time ($<0.15\text{ ms}$ latency):

$$\text{OBI}_t = \frac{\sum_{i=1}^{K} Q_{bid, i} - \sum_{i=1}^{K} Q_{ask, i}}{\sum_{i=1}^{K} Q_{bid, i} + \sum_{i=1}^{K} Q_{ask, i}} \in [-1.0, 1.0]$$

```
Time Domain (100ms Ticks)            Frequency Domain (Real FFT & PSD)
+-------------------------+          +----------------------------------+
| Raw OBI + Ghost Walls   |  ====>   | Low-Freq (0.05-0.8 Hz)  -> RLR   |
| High-Frequency Churn    |  (rfft)  | High-Freq (1.0-5.0 Hz)  -> BSI   |
+-------------------------+          +----------------------------------+
                                                      ||
                                                      \/ (Inverse FFT Low-Pass)
                                     +----------------------------------+
                                     | De-Spoofed "Clean OBI" Output   |
                                     +----------------------------------+
```

1. **Real Liquidity Ratio (RLR):** Measures the ratio of persistent, resting institutional liquidity ($0.05\text{ Hz} \le f < 0.8\text{ Hz}$) relative to total energy. $\text{RLR} \ge 0.70$ indicates organic depth.
2. **Bot Spoofing Index (BSI):** Identifies concentrated cyclic quote-stuffing harmonics in the $1.0\text{ Hz} - 5.0\text{ Hz}$ band. If $\text{BSI} \ge 0.35$, trade execution is vetoed.
3. **Clean OBI (Inverse FFT):** Strips high-frequency noise and returns an unpolluted imbalance metric to the decision logic.

*Full mathematical proof and benchmarking:* See [docs/MICROSTRUCTURE_FFT.md](docs/MICROSTRUCTURE_FFT.md).

---

## 🛡️ V5.5 Production Shields & Execution Rules

```
                      +------------------------------------+
                      |    ENTRY CANDIDATE DETECTED        |
                      +------------------------------------+
                                         |
                       [Is Symbol under 3m Cooldown?]
                                   /           \
                                (Yes)          (No)
                                 /               \
                       [ABORT ENTRY]       [Is 4H BTC Trend Aligned?]
                                                   /              \
                                                (No)              (Yes)
                                                 /                  \
                                     [ABORT ENTRY]        [Is FVG Depth 0.20%-1.50%?]
                                                                    /             \
                                                                 (No)             (Yes)
                                                                  /                 \
                                                      [ABORT ENTRY]       [Is ADX > 18 & OBI >= 0.30?]
                                                                                    /             \
                                                                                 (No)             (Yes)
                                                                                  /                 \
                                                                      [ABORT ENTRY]       [DISPATCH ORDER]
```

- **3-Minute Symbol Cooldown (`COOLDOWN_SECONDS = 180`):** After closing a position in a symbol, re-entry is blocked for 180 seconds to avoid commission bleed in whipsaw conditions.
- **60-Second Minimum Hold (`MIN_HOLD_SECONDS = 60`):** Absorbs sub-second LOB noise before allowing heuristic exits (hard stop remains active at all times).
- **Hard Stop Loss Cap (`0.70%`):** Maximum allowable risk on any individual trade; prevents catastrophic tail-risk slippage.
- **Dynamic Structural SL:** Positioned with a $0.20\%$ buffer beyond the structural FVG boundary (`fvg_top * 1.0020` for Shorts, `fvg_bot * 0.9980` for Longs).
- **Dynamic Break-Even & Trailing:** Locks break-even at $+0.45\%$ profit; engages continuous trailing with a $0.25\%$ callback above $+0.50\%$.
- **Profit-Protected Exit:** Once in profit, OBI threshold remains $\pm 0.35$ and requires 1-minute CVD confirmation before early liquidation.

---

## 💻 Interactive Live Terminal & Dashboard

The modern React + Tailwind web interface provides sub-second visibility into bot operations and quantitative telemetry:

- **Live Terminal:** Real-time visual OBI gauge, dynamic SMC context status (`BULLISH_FVG`, `BEARISH_FVG`, `NEUTRAL`), FVG depth meter, and real-time PnL tracking.
- **TradingView Pro Integration:** Embeds real-time Binance USDT-M Perpetual contract charts directly in the UI.
- **Dual PnL Display (Maker / Taker):** Automatically calculates both gross PnL and net PnL accounting for Binance VIP fee tiers ($0.02\%$ Limit/Maker vs. $0.05\%$ Market/Taker).
- **Market Screener Heatmap:** Live ranking of 150+ perpetual pairs showing spread, volume, FVG proximity, and institutional attraction score.
- **Version Switcher:** Seamlessly switch between V5.5 PROD, V5.4, and historical baseline analytics.

---

## 📂 Repository Structure

```ascii
spectral-lob-trading/
├── agent/                       # Reinforcement Learning environment and models (PPO)
│   ├── environment.py           # Gym trading environment with position context
│   ├── models.py                # Actor-Critic policy neural architectures
│   └── reward.py                # Asymmetric risk-adjusted reward functions
├── config/                      # System configuration & environment settings
│   └── settings.py              # Pydantic BaseSettings with typed validation
├── data/                        # Local IPC cache & benchmark datasets
│   ├── active_screener.json     # Dynamic screener inter-process memory buffer
│   ├── v5_5_optimized_backtest.csv  # 30-coin historical validation dataset
│   └── v5_3_vs_v5_4_trade_comparison.csv
├── docs/                        # In-depth technical reports & documentation
│   ├── MICROSTRUCTURE_FFT.md    # Fourier transform & spectral de-spoofing guide
│   ├── RESEARCH_REPORT.md       # Empirical research and failure diagnosis
│   └── VERSIONS.md              # Historical version progression log
├── features/                    # High-frequency feature engineering
│   ├── cvd_features.py          # Cumulative Volume Delta & aggression tracking
│   ├── frequency_features.py    # Real FFT spectral analyzer (RLR, BSI, Clean OBI)
│   ├── orderbook_features.py    # Microstructure 100ms OBI calculator
│   ├── smc_features.py          # 3m/5m Fair Value Gap (FVG) and Order Block detector
│   └── state_builder.py         # Multi-factor normalized state vector builder
├── frontend/                    # Modern React 18 + Vite live monitoring dashboard
│   ├── src/
│   │   ├── components/          # Reusable UI widgets (OBI meter, charts, stat cards)
│   │   ├── context/             # Real-time WebSocket and Supabase context providers
│   │   ├── pages/               # Dashboard, LiveTerminal, Screener, TradeLogs
│   │   └── utils/tradeLogic.js  # Dual Maker/Taker fee & PnL calculation engine
│   └── package.json
├── scripts/                     # Executable agents, screeners, and backtest suites
│   ├── market_screener.py       # 150+ futures market screener microservice
│   ├── run_dynamic_smc.py       # V5.5 PROD Live Execution Sniper Engine
│   ├── test_spectral_analyzer.py# LOB FFT unit test & benchmark harness
│   └── test_v5_5_enhancements.py# 30-coin comprehensive backtest simulation
├── utils/                       # Shared utility libraries
│   ├── btc_regime.py            # 4H Bitcoin Macro Regime detector (EMA50)
│   ├── database.py              # Supabase PostgreSQL connection pooler client
│   ├── logger.py                # Colorized structured logging
│   └── notifier.py              # Telegram alert dispatcher with retry fallback
├── vm_deploy/                   # Headless cloud deployment scripts
│   ├── start_v5_linux.sh        # Starts Screener and Sniper under detached tmux sessions
│   └── stop_headless_linux.sh   # Cleanly terminates running daemon processes
├── .env.example                 # Safe environment template (Zero secrets)
├── .gitignore                   # Comprehensive exclusion rules (Guards against leaks)
└── requirements.txt             # Python runtime dependencies
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and `npm`
- (Optional) Free Supabase project for telemetry and database synchronization
- (Optional) Binance API credentials (for live order execution; read-only market data works without keys)

---

### 2. Environment Setup

Clone the repository and prepare your local environment file:

```bash
git clone https://github.com/huseyin-yigit-ulker/spectral-lob-trading.git
cd spectral-lob-trading

# Copy the safe environment template
cp .env.example .env
```

Open `.env` and fill in your settings:

```env
# Binance Futures API (Optional for read-only market listening)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=true

# Database (Supabase PostgreSQL Connection String)
DB_CONNECTION_STRING=postgresql://postgres.your_project_ref:your_password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
SUPABASE_DB_URL=postgresql://postgres.your_project_ref:your_password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# Telegram Real-Time Notifications (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> **Security Note:** The `.env` file is strictly ignored by `.gitignore`. Never commit API keys, secrets, or database passwords to source control.

---

### 3. Backend Setup

```bash
# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the 15-minute Market Screener Microservice
python scripts/market_screener.py

# In a separate terminal, launch the V5.5 PROD Live Execution Agent
python scripts/run_dynamic_smc.py
```

---

### 4. Frontend Dashboard Setup

```bash
cd frontend

# Copy frontend env template (Optional for Supabase UI sync)
cp .env.example .env

# Install packages
npm install

# Start Vite development server
npm run dev
```

Navigate to `http://localhost:5173` to open the interactive live terminal.

---

### 5. Headless Daemon Deployment (Ubuntu / Cloud VM)

For production deployment on an AWS / DigitalOcean / Hetzner Linux VM:

```bash
# Launch both Screener and Sniper in detached background tmux sessions
chmod +x vm_deploy/*.sh
./vm_deploy/start_v5_linux.sh

# To view live bot logs:
tmux attach -t v5_bot

# To cleanly terminate all processes:
./vm_deploy/stop_headless_linux.sh
```

---

## 🔬 In-Depth Research Reports

For quantitative researchers, algorithmic traders, and engineers interested in the mathematical formulations and empirical logs:
- 📖 [**Quantitative Research & Failure Analysis (docs/RESEARCH_REPORT.md)**](docs/RESEARCH_REPORT.md)
- ⚡ [**Limit Order Book Spectral Analysis & FFT De-Spoofing (docs/MICROSTRUCTURE_FFT.md)**](docs/MICROSTRUCTURE_FFT.md)
- 📜 [**Complete Version Evolution & Post-Mortem History (docs/VERSIONS.md)**](docs/VERSIONS.md)

---

## 🔒 Security & Privacy Notice

This repository has undergone automated and manual security audits:
- **Zero hardcoded credentials:** All API keys, database connection URIs, and notification tokens are loaded strictly via environment variables.
- **Git History Cleanliness:** Commits, branches, and trees across the entire git history have been verified using regex pattern scanning to ensure zero private key or credential leaks.
- **Graceful Fallbacks:** The frontend and backend gracefully degrade to simulated stubs if external services (Supabase, Binance, Telegram) are not configured.

---

## ⚖️ Disclaimer

*This software is published for educational and research purposes only. Algorithmic trading in cryptocurrency futures involves substantial financial risk and can result in the loss of all invested capital. Past backtested or live performance does not guarantee future results. Never trade with capital you cannot afford to lose.*

---

<div align="center">
Developed with ❤️ by <a href="https://github.com/huseyin-yigit-ulker">Hüseyin Yiğit Ülker</a>
</div>
