# Orders Signal - Mikro-Yapı & SMC Tabanlı Otonom Trading Ajanı

Orders Signal is an autonomous trading agent designed to trade on Binance Futures using Order Book Imbalance (OBI), Cumulative Volume Delta (CVD), and Smart Money Concepts (SMC) via Reinforcement Learning.

## Architecture Overview (Mimari Genel Bakış)

Bu proje, mikro-yapı verilerini (emir defteri dengesizliği, CVD) ve fiyat aksiyonu konseptlerini (SMC) birleştirerek derin pekiştirmeli öğrenme (Deep RL) ile alım satım kararları alan otonom bir sistemdir.

- **Data Collection (Veri Toplama):** Binance Futures WebSocket API üzerinden yüksek frekanslı depth ve trade verilerinin toplanması.
- **Feature Engineering:** Toplanan verilerin işlenerek OBI, CVD ve SMC özelliklerinin çıkarılması.
- **RL Agent:** Çıkarılan özelliklerle eğitilmiş ajanın piyasa yönünü tahmin etmesi ve işlem kararları alması.
- **Execution (Gerçekleştirme):** Binance Futures API üzerinden kararların asenkron olarak uygulanması (Testnet ve Dry-run desteğiyle).
- **Monitoring (İzleme):** Terminal tabanlı canlı dashboard (Rich kütüphanesi).

## Project Structure (Proje Yapısı)

```text
orders_signal/
├── execution/
│   └── binance_executor.py
├── monitoring/
│   └── dashboard.py
├── scripts/
│   ├── collect_data.py
│   └── run_agent.py
├── main.py
└── README.md
```

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Setup environment variables:
   Create a `.env` file in the root directory:
   ```env
   BINANCE_API_KEY=your_api_key
   BINANCE_API_SECRET=your_api_secret
   ```

## Usage

You can use the `main.py` entry point to access different modules:

```bash
# Start data collection
python main.py collect --symbol BTCUSDT

# Train the RL agent
python main.py train

# Run live trading (use with caution)
python main.py live --dry-run

# Start monitoring dashboard
python main.py monitor
```

## Configuration
All configuration parameters (symbols, refresh rates, model paths) can be set via environment variables or configuration files in the future.

## Development Roadmap
- [x] Basic project scaffolding
- [ ] Data collection module integration
- [ ] Feature engineering pipeline
- [ ] RL environment and training scripts
- [ ] Live execution module implementation

## Tech Stack
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Binance](https://img.shields.io/badge/Binance-FCD535?style=for-the-badge&logo=binance&logoColor=white)

## 📈 Kuralcı Bot Stratejisi (Gerçek Makro)

Yapay zeka (RL) modellerinin komisyon ücretleri nedeniyle HFT (Yüksek Frekanslı Ticaret) alanında zorlanması üzerine, başarılı kâr oranına sahip (`+%1.28 Net`) bir "Kuralcı (Heuristic) Makro Bot" geliştirilmiştir.

### Strateji Mimarisi:
Bu bot, piyasadaki gürültüyü (noise) ve sahte duvarları (spoofing) engellemek için üç temel matematiksel filtre kullanır:

1. **60-Saniyelik Makro OBI (Emir Defteri Dengesizliği):**
   * Saniyelik OBI dalgalanmaları yerine, son 60 saniyenin hareketli ortalaması (MA) alınır. Bu, anlık manipülasyonları filtreler.
2. **CVD (Kümülatif Hacim) Gerçeklik Onayı:**
   * Balinalar emir defterine devasa bir alış duvarı koyup fiyatı manipüle edebilir (Spoofing). Bot, bu duvara inanmak için **CVD_1m > 0** (gerçekten market alışları yapılıyor mu?) onayını zorunlu tutar.
3. **Hysteresis (Yapışkanlık / Ölü Bölge):**
   * Aşırı işlem (Overtrading) yapıp komisyonlara para kaptırmamak için asimetrik giriş/çıkış sınırları belirlenmiştir.
   * **LONG Giriş:** Makro OBI `> 0.30` ve CVD pozitif.
   * **LONG Çıkış:** Makro OBI `< -0.05` (Trendin tersine döndüğüne dair hafif bir kanıt).
   * Aradaki bölgede (-0.30 ile 0.30 arası) bot tamamen "Sağır ve Dilsiz" davranarak **Ölü Bölgede (Dead Zone)** bekler. Bu sayede işlem sayısı binlerden ~170 bandına düşürülür.

