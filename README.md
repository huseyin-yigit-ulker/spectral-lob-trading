# 🤖 Otonom Kripto Ticaret Ajanı (HFT & RL)

Bu proje, Binance Futures (Vadeli İşlemler) piyasası üzerinde **Yüksek Frekanslı Ticaret (HFT)** verilerini toplayan, Emir Defteri Dengesizliği (OBI) ve Kümülatif Hacim (CVD) metriklerini kullanarak karar veren ve **Derin Pekiştirmeli Öğrenme (Deep Reinforcement Learning - PPO)** ile kendi kendini eğiten otonom bir ticaret ajanıdır.

## 🚀 Temel Özellikler

### 1. Kesintisiz Veri Madenciliği (`collect_data.py`)
- Binance WebSockets üzerinden doğrudan `depth20@100ms` (Milisaniyelik Emir Defteri) ve `trade` (Gerçekleşen İşlemler) kanallarına bağlanır.
- Verileri hiçbir veri kaybı olmadan ham halleriyle, sıkıştırılmış **Parquet (.parquet)** dosyaları halinde kaydeder.
- Sistem çökmelerine karşı "Auto-Flush" koruması içerir.

### 2. Gerçek Zamanlı Makro İzleyici (`run_agent.py`)
- HFT piyasasındaki saniyelik sahte gürültüleri engellemek için **Gerçek Makro (True Macro)** mantığıyla çalışır.
- 60 saniyelik hareketli ortalama, `+0.30 OBI` eşiği ve hacim `(CVD > 0)` onayı ile sahte (spoofing) emirlere aldanmadan çalışır.
- `Rich` kütüphanesi ile tasarlanmış modern bir canlı terminal panosu (Dashboard) sunar. Coinlerin kendi değerlerine göre dinamik ondalık hassasiyeti uygular.

### 3. Simülasyon ve Backtest (`backtest_macro.py`)
- Canlı ajandaki 60 saniyelik katı kısıtlamaları, toplanan geçmiş veriler üzerinde milisaniyesine kadar simüle eder.
- Kâr-Zarar (PnL) durumunu, işlem sayısını ve piyasa ile botun performans karşılaştırmasını grafiksel olarak (PNG) ve döküm olarak (CSV) sunar.

### 4. Yapay Zeka (PPO) Eğitmeni (`train_agent.py`)
- **Stable Baselines3** altyapısını kullanarak, toplanan Order Book verileri üzerinde PPO (Proximal Policy Optimization) modelini eğitir.
- Ajan, 100ms'lik veri adımlarında kârı maksimize edecek, komisyon zararından kaçınacak kararları deneme-yanılma (Reinforcement Learning) yoluyla öğrenir.

## 🛠️ Kurulum

```bash
# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# Veri toplamaya başlayın (Örn: BTCUSDT)
python scripts/collect_data.py --symbol BTCUSDT

# Canlı dashboard'u başlatın
python scripts/run_agent.py --symbol BTCUSDT

# Yapay Zeka ajanını eğitin
python scripts/train_agent.py --symbol BTCUSDT --timesteps 500000
```

## 🧠 Strateji Özeti
Sistem, tahtadaki ilk 5 kademe yığılmasına (OBI) bakarak piyasadaki potansiyel patlamaları sezer. Ancak sahte yığılmalara düşmemek için `CVD_1m` (Son 1 dakikalık gerçek alıcı/satıcı hacmi) onayını bekler. Tüm koşullar karşılandığında sinyal üretir.
