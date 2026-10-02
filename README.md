# 🧠 HFT & SMC Kantitatif İşlem Algoritması (Binance Futures)

Bu proje, yüksek frekanslı emir defteri verilerini (Order Book Imbalance & Cumulative Volume Delta) Kurumsal Akıllı Para (Smart Money Concepts - FVG/OB) yapılarıyla birleştiren mikromimari tabanlı bir algoritmik ticaret sistemidir. Sistem, sahte likidite duvarlarını (spoofing) filtreleyerek sadece yüksek olasılıklı pusu işlemlerini (Sniper) hedefler.

## 📁 Klasör Yapısı (Folder Structure)

* **`features/`**: Özellik mühendisliği (Feature Engineering) modüllerini içerir.
  * `cvd_features.py`: Alıcı/Satıcı agresifliğini (Trade verisi) ölçer.
  * `orderbook_features.py`: 100ms hızındaki derinlik verisinden OBI hesaplar.
  * `smc_features.py`: Kendi özel algoritmamızla 3m ve 5m FVG (Likidite Boşluğu) haritasını çıkarır.
  * `state_builder.py`: Makine öğrenmesi modelleri için verileri normalize eder.
* **`scripts/`**: Çalıştırılabilir ana ajanları (Botları) barındırır. Her versiyonun botu buradadır (Detaylar aşağıda).
* **`notebooks/`**: Algoritmanın başarısını test eden Quant analiz araçlarıdır. 
  * `Islem_Analizi.ipynb`: Geçmiş logları okuyup komisyon dahil net kârı (PnL) simüle eder.
  * `SMC_Backtest.ipynb`: Zaman makinesi mantığıyla geçmiş HFT işlemlerini SMC filtresinden geçirerek Win Rate optimizasyonu yapar.
* **`data/`**: Mikroservislerin kendi aralarında haberleştiği RAM-Disk benzeri JSON önbellek (cache) klasörüdür.
* **`logs/`**: Ajanların ürettiği AL/SAT sinyallerinin saniyesi saniyesine kaydedildiği CSV klasörüdür.
* **`vm_deploy/`**: Projeyi bulut sunuculara (Ubuntu/Linux) kurmak için gerekli paketler ve başlatma scriptleridir (`start.sh`).

---

## 🚀 Versiyonlar ve Evrim Süreci

### V1 & V2: Veri Madencisi (Multi-Agent)
* **Dosya:** `scripts/run_multi_agent.py`
* **Mantık:** Sabit 100 coini takip eder. SMC (Bağlam) bilmez, sadece OBI (Emir Defteri) +0.40 olduğunda körü körüne işleme girer.
* **Amacı:** Piyasada hangi coinlerin toksik (hantal) olduğunu, hangi coinlerin bot dostu olduğunu anlamak için 7/24 çalışıp veri (log) toplar.
* **Çıktı (Output):** `logs/multi_signals_*.csv`

### V3: Statik Keskin Nişancı (Sniper Agent)
* **Dosya:** `scripts/run_sniper_agent.py`
* **Mantık:** V2'nin ürettiği binlerce işlemin analizi sonucunda BTC, ETH, BNB gibi komisyon düşmanı ağır coinler atılmış; sadece en kârlı 15 coin (MANA, SOL, AVAX vb.) hedeflenmiştir. 
* **Çıktı:** `logs/sniper_signals_*.csv`

### V4: SMC Filtreli HFT (Akıllı Para Ajanı)
* **Dosya:** `scripts/run_smc_agent.py`
* **Mantık:** 15 Altın Coini takip eder. Ancak OBI patlasa bile, fiyat eğer 3m veya 5m mum grafiğinde bir FVG (Likidite Boşluğu) içinde değilse işlemi reddeder (Sinyal: BEKLE). Backtest sonucunda %39 Win Rate'i **%66.67'ye** fırlatmıştır.
* **Çıktı:** `logs/smc_signals_*.csv`

### V5: Tam Dinamik Kurumsal Mimari (Microservices)
Piyasa koşulları sürekli değiştiği için sabit 15 coin mantığı terk edilmiş, sistem asenkron haberleşen iki bağımsız mikroservise bölünmüştür:

**1. Dinamik İzci (Screener):** `scripts/market_screener.py`
* Her 15 dakikada bir Binance USDT vadeli işlemlerindeki 150+ coini tarar. 
* Spread'i %0.06'dan büyük olanları ve Hacmi 50M$ altı olanları çöpe atar. 
* Kalanları FVG'ye yakınlıklarına (Proximity) ve RVOL (Hacim artışı) durumuna göre puanlar.
* **Çıktı:** En iyi 15 "Pusu Coinini" bulur ve `data/active_screener.json` dosyasına yazar.

**2. Dinamik Tetikçi (Dynamic SMC Agent):** `scripts/run_dynamic_smc.py`
* Canlı olarak piyasayı izler. Her 15 saniyede bir JSON dosyasını dinler.
* Tarayıcı (Screener) yeni bir coin bulduğunda kendini kapatmadan eski kanalları (WebSocket) iptal edip yeni coinlere bağlanır.
* SMC onayı aldığında tetiği çeker.
* **Çıktı:** `logs/dynamic_smc_signals_*.csv`

---

## ⚙️ Girdi ve Çıktılar (Input / Output Pipeline)

* **Girdi (Input):**
  * `Binance REST API`: Geçmiş mum verileri (FVG çizimi için).
  * `Binance WebSocket`: Saniyede 10 kez gelen `@depth20@100ms` (Derinlik), `@trade` (Alım-Satım) ve `@kline` (Mum kapanış) verileri.
* **Çıktı (Output Log Formatı):**
  * Her işlem CSV formatında loglanır:
  * `Zaman | Sembol | Fiyat | Macro_OBI | CVD_1m | SMC_Context (BULLISH_FVG) | Sinyal_Yonu`
