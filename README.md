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

### V1 & V2: Veri Madencisi (Multi-Agent)
* **Dosya:** `scripts/run_multi_agent.py`
* **Mantık:** Sabit 100 coini takip eder. SMC (Bağlam) bilmez, sadece OBI (Emir Defteri) +0.40 olduğunda körü körüne işleme girer.
* **Amacı:** Piyasada hangi coinlerin toksik (hantal) olduğunu, hangi coinlerin bot dostu olduğunu anlamak için 7/24 çalışıp makine öğrenmesi için veri (log) toplar.

### V3: Statik Keskin Nişancı (Sniper Agent)
* **Dosya:** `scripts/run_sniper_agent.py`
* **Mantık:** V2'nin ürettiği binlerce işlemin analizi sonucunda BTC, ETH, BNB gibi komisyon düşmanı ağır coinler atılmış; sadece en kârlı 15 coin (MANA, SOL, AVAX vb.) hedeflenmiştir. 

### V4: SMC Filtreli HFT (Akıllı Para Ajanı)
* **Dosya:** `scripts/run_smc_agent.py`
* **Mantık:** 15 Altın Coini takip eder. Ancak OBI patlasa bile, fiyat eğer 3m veya 5m mum grafiğinde bir FVG (Likidite Boşluğu) içinde değilse işlemi reddeder (Sinyal: BEKLE). Backtest sonucunda %39 Win Rate'i **%66.67'ye** fırlatmıştır.

### V5: Tam Dinamik Kurumsal Mimari (Microservices)
Piyasa koşulları sürekli değiştiği için sabit 15 coin mantığı terk edilmiş, sistem asenkron haberleşen iki bağımsız mikroservise bölünmüştür:

**1. Dinamik İzci (Screener):** `scripts/market_screener.py`
* Her 15 dakikada bir Binance USDT vadeli işlemlerindeki 150+ coini tarar. 
* Spread'i %0.06'dan büyük olanları ve Hacmi 50M$ altı olanları çöpe atar. 
* **Kara Liste (Blacklist):** PAXG, XAUT (Altın stabil tokenları) ve PUMP gibi manipülatif çöp coinler koda gömülü liste ile sonsuza dek reddedilir.
* Kalanları FVG'ye yakınlıklarına (Proximity) ve RVOL (Hacim artışı) durumuna göre puanlar. En iyi 15 coini bulup `data/active_screener.json` dosyasına yazar.

**2. Dinamik Tetikçi (Dynamic SMC Agent):** `scripts/run_dynamic_smc.py`
* Canlı olarak piyasayı izler. Her 15 saniyede bir JSON dosyasını dinler ve yeni coinlere bağlanır.
* SMC onayı ve OBI ivmesi eşleştiğinde tetiği çeker.
* **Yapısal FVG Stop-Loss (Structural Stop):** Sadece OBI'ye bakarak çıkmaz. İşleme girdiği salise FVG kutusunun bittiği noktaya %0.05 toleransla "Yapısal Stop" koyar. Fiyat ihlal edildiğinde inat etmez, spoofing (sahte duvar) tuzaklarından otomatik kurtulur.

---

## ☁️ Sunucu (VM / Cloud) Dağıtımı

Sistemin uzak bulut sunucularında 7/24 tamamen kendi kendine çalışabilmesi için `vm_deploy/` klasörüne özel **Headless (Görünmez)** scriptler eklenmiştir:

* **`start_headless_linux.sh`**: Linux (Ubuntu) sunucularda Akıllı Python Dedektörü ve `nohup` kullanarak V2 Veri Madencisini ve V5 Dinamik Mimarisi'ni işletim sisteminin arka planına gömer. SSH bağlantısı veya VS Code kapatılsa dahi botlar çalışmaya devam eder.
* **`stop_headless_linux.sh`**: Arka plandaki tüm python işlemlerini temiz bir şekilde sonlandırır.
* *(Aynı işlemlerin Windows VM'leri için olan PowerShell `.ps1` versiyonları da mevcuttur).*

---

## 📊 Girdi ve Çıktılar (Input / Output Pipeline)

* **Girdi (Input):** `Binance REST API` (FVG Çizimi) & `Binance WebSocket` (@depth20, @trade, @kline)
* **Çıktı (Output Log Formatı):** `Zaman | Sembol | Fiyat | Macro_OBI | CVD_1m | SMC_Context | Sinyal_Yonu`
