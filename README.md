# 🤖 HFT Orders & Signal Autonomous Agent (Private Core)

Bu proje, Binance Futures (USDT-M) piyasasında **Yüksek Frekanslı Ticaret (HFT)** dinamiklerini kullanan gizli ve otonom bir ticaret ajanıdır. Sıradan indikatörler (RSI, MACD) yerine kurumsal piyasa yapıcıların kullandığı **Emir Defteri Dengesizliği (OBI)** ve **Kümülatif Hacim Deltası (CVD)** tabanlı algoritmalarla çalışır. Ayrıca sistem, **PPO (Proximal Policy Optimization)** tabanlı bir Reinforcement Learning (Pekiştirmeli Öğrenme) yapay zeka ajanına ev sahipliği yapar.

## 🏗️ Proje Mimarisi ve Akışı

Proje 4 temel modülden oluşmaktadır:
1. **Veri Toplayıcı** (`scripts/collect_data.py`)
2. **Gerçek Zamanlı Karar Motoru** (`scripts/run_agent.py`)
3. **Gerçek Makro Backtester** (`scripts/backtest_macro.py`)
4. **PPO (Yapay Zeka) Eğitmeni** (`scripts/train_agent.py`)

---

## 📊 1. Veri Madenciliği (Data Mining)
Sistem gecikmeyi minimize etmek için mum verisi kullanmaz. Binance WebSockets üzerinden doğrudan şu iki kanala bağlanır:

* **`depth20@100ms` (Emir Defteri):** Saniyede 10 kez güncellenir. Tahtadaki en iyi 20 Alış (Bid) ve 20 Satış (Ask) kademesindeki yığılmaları yakalar.
* **`trade` (Gerçekleşen İşlemler):** Milisaniye hızında akan anlık alım satımları (Taker/Maker detaylarıyla) alır. *(Not: Binance'in aggTrade kanalındaki gizli kısıtlamaları by-pass edilerek doğrudan `trade` kanalı tercih edilmiştir).*

**Kayıt Formatı:** Veriler milisaniyelik boyutta şişmemesi ve yapay zeka eğitiminde çok hızlı (vectorized) okunabilmesi için `.parquet` formatında `data/` dizinine kaydedilir.

---

## 🧠 2. Gizli Strateji ve Karar Mekanizması ("Gerçek Macro")
Canlı ajan, piyasadaki "Spoofing" (Sahte Emir Duvarı) tuzaklarına düşmemek için **Hysteresis (Tolerans Bantları)** ile donatılmış kati bir algoritmaya sahiptir.

**Strateji Kriterleri:**
* **Zaman Penceresi:** Son 10 saniyelik verinin HFT dünyasında "çok gürültülü" olması sebebiyle **60 saniyelik (600 tick)** hareketli ortalama kullanılır.
* **LONG Sinyali Şartı:**
  1. `Macro OBI > +0.30`: Tahtadaki emirlerin en az %65'i net alış yönünde baskı kurmalı.
  2. `CVD_1m > 0`: Sadece tahtaya sahte emir girmek yetmez, son 1 dakikada **gerçekten** marketten alım yapan hacim (CVD) pozitif olmalıdır.
* **SHORT Sinyali Şartı:**
  1. `Macro OBI < -0.30`: Tahtadaki emirler güçlü satış yönlü olmalı.
  2. `CVD_1m < 0`: Son 1 dakikalık gerçek işlem hacmi satıcılı (negatif) olmalı.
* **İşlem Kapatma (Exit) Kriteri:** Fiyat yön değiştirdiğinde sinyalin `NOTR` (Bekle) durumuna geçmesi için OBI'nin sıfıra ulaşması yetmez, momentumun tersine dönerek `+/- 0.05` eşiğine kırılması beklenir.

*Bu katı kısıtlamalar sayesinde bot yatay (sideways) piyasalarda işlem açmayıp (komisyon tasarrufu yapar), sadece kesin ivme anlarında işleme girer.*

---

## 🤖 3. Derin Pekiştirmeli Öğrenme (RL - PPO)
Kural tabanlı stratejinin ötesinde sistemin kendi kendine optimize olması için `Stable Baselines3` altyapısı kullanılmıştır.

* **State (Gözlem Vektörü):** Yapay zeka ajanına şu 4'lü matris sunulur:
  - `OBI` (Anlık Dengesizlik)
  - `OBI_60s` (Makro Trend Eğilimi)
  - `Return_1s` (Fiyat Volatilitesi)
  - `Spread` (Likidite/Makas)
* **Action (Aksiyon Uzayı):** `[0: SHORT, 1: BEKLE, 2: LONG]`
* **Reward (Ödül Fonksiyonu):** 
  - İşlem açıldığında/kapandığında **Komisyon Cezası** kesilir.
  - Sadece izleyip risk almadığı her saniye için mikro bir **Hareketsizlik Cezası** uygulanır.
  - Açtığı pozisyon doğru yönde ilerlerse, PnL (Gerçekleşen Kâr) yüksek bir skaler değerle çarpılarak ajana ödül olarak verilir.

Eğitim bittiğinde elde edilen ağırlık dosyası `models/ppo_symbol_v1.zip` dizinine kaydedilir.

---

## 💻 Kullanım Komutları

```bash
# Gerekli bagimliliklar
pip install -r requirements.txt

# 1. Ham Veri Toplama (Arka planda acik kalmali)
python scripts/collect_data.py --symbol BTCUSDT

# 2. Canli Sinyal ve Dashboard Izleyici
python scripts/run_agent.py --symbol BTCUSDT

# 3. Kendi Bilgisayarinda YZ (PPO) Egitimi
python scripts/train_agent.py --symbol BTCUSDT --timesteps 500000

# 4. Kural Tabanli Gecmis Strateji Testi
python scripts/backtest_macro.py
```
