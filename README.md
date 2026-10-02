# 🚀 HFT & SMC Kantitatif İşlem Algoritması (Binance Futures)

Bu proje, yüksek frekanslı emir defteri verilerini (Order Book Imbalance & Cumulative Volume Delta) Kurumsal Akıllı Para (Smart Money Concepts - FVG/OB) yapılarıyla birleştiren mikromimari tabanlı bir algoritmik ticaret sistemidir. Sistem, sahte likidite duvarlarını (spoofing) filtreleyerek sadece yüksek olasılıklı pusu işlemlerini (Sniper) hedefler.

## 📂 Klasör Yapısı (Folder Structure)
* **`features/`**: Özellik mühendisliği (Feature Engineering) modüllerini içerir.
  * `cvd_features.py`: Alıcı/Satıcı agresifliğini (Trade verisi) ölçer.
  * `orderbook_features.py`: 100ms hızındaki derinlik verisinden OBI hesaplar.
  * `smc_features.py`: Kendi özel algoritmamızla 3m ve 5m FVG (Likidite Boşluğu) haritasını çıkarır.
  * `state_builder.py`: Makine öğrenmesi modelleri için verileri normalize eder.
* **`scripts/`**: Çalıştırılabilir ana ajanları (Botları) barındırır. Her versiyonun botu buradadır.
* **`notebooks/`**: Algoritmanın başarısını test eden Quant analiz araçlarıdır. 
  * `Islem_Analizi.ipynb`: Geçmiş logları okuyup komisyon dahil net kârı (PnL) simüle eder.
  * `SMC_Backtest.ipynb`: Zaman makinesi mantığıyla geçmiş HFT işlemlerini SMC filtresinden ve Yapısal Stop testinden geçirir.
* **`data/`**: Mikroservislerin kendi aralarında haberleştiği RAM-Disk benzeri JSON önbellek (cache) klasörüdür.
* **`logs/`**: Ajanların ürettiği AL/SAT sinyallerinin saniyesi saniyesine kaydedildiği CSV klasörüdür.
* **`vm_deploy/`**: Projeyi bulut sunuculara kurmak ve arka planda görünmez (Headless) çalıştırmak için gerekli scriptlerdir.

---

## 🧬 Versiyonlar ve Evrim Süreci

### 🛑 V1 & V2: Veri Madencisi (Multi-Agent) [KULLANILMIYOR / EMEKLİ]
* **Dosya:** `scripts/run_multi_agent.py`
* **Mantık:** Sabit 100 coini takip eder. SMC bilmeden, sadece OBI ile körü körüne işleme girer.
* **Durum:** Hantal coinlerdeki komisyon erimesi (Chop) ispatlandıktan sonra V5'e geçilmiş ve bu bot sunuculardan tamamen kaldırılmıştır. Artık Makine Öğrenmesi (RL) verileri doğrudan V5 botu üzerinden toplanmaktadır.

### V3: Statik Keskin Nişancı (Sniper Agent)
* **Mantık:** V2'nin ürettiği binlerce işlemin analizi sonucunda BTC, ETH, BNB gibi komisyon düşmanı ağır coinler atılmış; sadece en kârlı 15 coin hedeflenmiştir. 

### V4: SMC Filtreli HFT (Akıllı Para Ajanı)
* **Mantık:** OBI patlasa bile, fiyat eğer 3m veya 5m mum grafiğinde bir FVG (Likidite Boşluğu) içinde değilse işlemi reddeder. Backtest sonucunda %39 Win Rate'i **%66.67'ye** fırlatmıştır.

### 🏆 V5: Tam Dinamik Kurumsal Mimari (Microservices)
Sistem asenkron haberleşen iki bağımsız mikroservise bölünmüş ve hem para basan hem de kusursuz backtest verisi toplayan bir makineye dönüştürülmüştür:

**1. Dinamik İzci (Screener):** `scripts/market_screener.py`
* Her 15 dakikada bir Binance USDT vadeli işlemlerindeki 150+ coini tarar. Spread > %0.06 ve Hacim < 50M$ olanları eler.
* **Kara Liste (Blacklist):** PAXG, XAUT (Altın stabil) ve PUMP gibi manipülatif çöp coinler koda gömülü liste ile sonsuza dek reddedilir.
* **Tarihçe Loglayıcı (Backtest Data):** Her 15 dakikalık taramanın detaylarını `logs/screener_history_*.csv` dosyasına kaydeder. Neyi, neden reddettiğini (Spread, Hacim, Puan) loglar.

**2. Dinamik Tetikçi (Dynamic SMC Agent):** `scripts/run_dynamic_smc.py`
* Her 15 saniyede bir JSON dosyasını dinler ve yeni coinlere dinamik bağlanır.
* **Dar FVG Filtresi (Depth Filter):** Tespit edilen FVG'nin derinliği (üst-alt sınırı) **%0.10'dan daha küçükse** komisyon/slippage tuzağına düşmemek için işlemi otomatik reddeder.
* **Websocket Hata Koruması:** Binance sunucularından kaynaklı asenkron veri (Fiyat = 0.0) gelişlerinde sahte işlem açılmasını engeller.
* **Yapısal FVG Stop-Loss (Structural Stop):** İşleme girdiği salise FVG kutusunun sınırına %0.05 toleransla "Yapısal Stop" koyar. Fiyat sınır dışına taştığında OBI'yi beklemeden işlemi anında keser (Sahte duvar/Spoofing kalkanı).

---

## ☁️ Sunucu (VM / Cloud) Dağıtımı

Sistemin uzak bulut sunucularında 7/24 tamamen kendi kendine çalışabilmesi için `vm_deploy/` klasörüne özel **Headless (Görünmez)** scriptler eklenmiştir:

* **`start_headless_linux.sh`**: Linux (Ubuntu) sunucularda Akıllı Python Dedektörü ve `nohup` kullanarak **V5 İzci ve V5 Tetikçi** botlarını işletim sisteminin arka planına gömer. SSH bağlantısı veya terminal kapatılsa dahi botlar çalışmaya devam eder.
* **`stop_headless_linux.sh`**: Arka plandaki tüm python işlemlerini temiz bir şekilde sonlandırır.
* *(Aynı işlemlerin Windows VM'leri için olan PowerShell `.ps1` versiyonları da mevcuttur).*

---

## 📊 Girdi ve Çıktılar (Input / Output Pipeline)

* **Girdi (Input):** `Binance REST API` (FVG Çizimi) & `Binance WebSocket` (@depth20, @trade, @kline)
* **Çıktı (Agent Log Formatı):** `Zaman | Sembol | Fiyat | Macro_OBI | CVD_1m | SMC_Context | FVG_Top | FVG_Bottom | FVG_Depth_Pct | Sinyal_Yonu | Aktif_SL`
* **Çıktı (Screener Log Formatı):** `Zaman | Sembol | Fiyat | Hacim | Spread | FVG_Mesafe_Yuzde | Skor | Durum`
