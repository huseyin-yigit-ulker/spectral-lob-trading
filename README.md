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
* Her 15 dakikada bir Binance USDT vadeli işlemlerindeki 150+ coini tarar. Spread > %0.06 ve Hacim < 150M$ olanları eler. (Düşük hacimli manipülatif coinlerden kaçınmak için hacim filtresi 150 Milyon Dolara çıkarıldı).
* **Kara Liste (Blacklist):** PAXG, XAUT (Altın stabil) ve PUMP gibi manipülatif çöp coinler koda gömülü liste ile sonsuza dek reddedilir.
* **Genişletilmiş Radar:** WS bağlantısı limiti 15'ten 40'a yükseltildi, daha geniş bir fırsat havuzu izlenir. DB'yi yormamak adına screener logları veritabanına yazılmaz, sadece JSON üzerinden izlenir.

**2. Dinamik Tetikçi (Keskin Nişancı):** `scripts/run_dynamic_smc.py`
* Her 15 saniyede bir JSON dosyasını dinler ve yeni coinlere dinamik bağlanır.
* **Dar FVG Filtresi (Depth Filter):** Tespit edilen FVG'nin derinliği (üst-alt sınırı) **%0.20'den daha küçükse** komisyon/slippage tuzağına düşmemek için işlemi otomatik reddeder. (Eski kural olan %0.05, stopların erken patlamasına sebep olduğu için %0.20'ye güncellendi).
* **Kuvvetli OBI Filtresi:** İşleme girmek için Emir Defteri Dengesizliğinin (OBI) en az **0.30** olması zorunludur. (Sınırda kalan cılız tepkileri elemek için).
* **Websocket Hata Koruması:** Binance sunucularından kaynaklı asenkron veri (Fiyat = 0.0) gelişlerinde sahte işlem açılmasını engeller.
* **Yapısal FVG Stop-Loss (Structural Stop):** İşleme girdiği salise FVG kutusunun sınırına %0.05 toleransla "Yapısal Stop" koyar. Fiyat sınır dışına taştığında OBI'yi beklemeden işlemi anında keser (Sahte duvar/Spoofing kalkanı).

---

## ☁️ Sunucu (VM / Cloud) Dağıtımı & Veritabanı (V2)

* Sistem **Supabase V2** PostgreSQL altyapısına taşınmış olup, tablolar Pooler (6543) üzerinden yönetilmektedir. Gereksiz screener datası V1'den silinmiş ve sistem sadece net sinyalleri (`trade_logs`) ve `live_metrics` tablosunu beslemektedir.

* **`start_headless_linux.sh`**: Linux (Ubuntu) sunucularda Akıllı Python Dedektörü ve `nohup` kullanarak **V5 İzci ve V5 Tetikçi** botlarını arka plana gömer. SSH bağlantısı kapatılsa dahi botlar çalışmaya devam eder.
* **`stop_headless_linux.sh`**: Arka plandaki tüm python işlemlerini temiz bir şekilde sonlandırır.

---

## 📊 Girdi ve Çıktılar (Input / Output Pipeline)

* **Girdi (Input):** `Binance REST API` (FVG Çizimi) & `Binance WebSocket` (@depth20, @trade, @kline)
* **Çıktı (Agent Log Formatı):** `Zaman | Sembol | Fiyat | Macro_OBI | CVD_1m | SMC_Context | FVG_Top | FVG_Bottom | FVG_Depth_Pct | Sinyal_Yonu | Aktif_SL`
* **Frontend Arayüzü (Premium UI):** 
  * **Unified Dashboard:** Kümülatif PnL (Bakiye) büyüme eğrisini anlık çizer. Açık olan (henüz kapanmamış) pozisyonları canlı radar olarak listeler.
  * **Market Scanner (Screener):** DB'yi şişirmemek adına screener verisi JSON olarak `active_screener` tablosunda tek satırda tutulur ve UI'a bir **Sıcaklık Haritası (Heatmap)** şeklinde yansıtılır. FVG'ye en yakın fırsatlar parlak yeşil olarak öne çıkar.
  * **Trade Logs & Live Terminal:** Sinyal geçmişi kartlarla sunulur. Canlı terminal OBI ve FVG verilerini profesyonel hacker ekranı tasarımıyla gösterir.
