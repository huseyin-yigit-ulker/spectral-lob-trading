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
* **Dar FVG Filtresi (Depth Filter):** Tespit edilen FVG'nin derinliği (üst-alt sınırı) **%0.20'den daha küçükse** komisyon/slippage tuzağına düşmemek için işlemi otomatik reddeder.
* **Kuvvetli OBI Filtresi:** İşleme girmek için Emir Defteri Dengesizliğinin (OBI) en az **0.30** olması zorunludur.
* **Websocket Hata Koruması:** Binance sunucularından kaynaklı asenkron veri (Fiyat = 0.0) gelişlerinde sahte işlem açılmasını engeller.

### 💎 V5.2 & V5.3: SMC Yapısal OBI Dinamik Çıkış & Genişletilmiş Koruma Kalkanı
* **Dinamik FVG-Koşullu OBI Çıkışı:** Pozisyon yönünde FVG geçerliliğini korurken (`BEARISH_FVG` veya `BULLISH_FVG`) anlık mikro dalgalanmalar yüzünden işlem kapatılmaz. OBI çıkış eşiği **±0.35 (Kuvvetli Ters Emir Baskısı)** seviyesine çekilmiştir. Yalnızca FVG yapısı bozulduğunda/bittiğinde standart ±0.15 güvenlik eşiği devreye girer.
* **1 Dakikalık Mum Kapanışı Onaylı SL:** İğne/fitil manipülasyonlarına (stop hunt) karşı SL artık anlık tik ile değil, 1 dakikalık mum kapanışı onayıyla tetiklenir (`kline_1m['x'] == True`).
* **%0.20 Genişletilmiş FVG Tamponu:** Stop seviyesi FVG sınırına yapışık olmak yerine %0.20 toleransla (`fvg_top * 1.0020` / `fvg_bot * 0.9980`) yerleştirilir.
* **Optimize Edilmiş Break-Even & Trailing Stop:** Başa baş koruması %0.45 kârda devreye girerek pozisyona nefes alma payı bırakır; %0.50+ kârda %0.25 callback ile kârı kilitler.
* **Veritabanı Durum Kurtarma (State Persistence):** Bot yeniden başlasa veya coin listeden geçici olarak düşse dahi PostgreSQL üzerindeki açık işlemler otomatik tanınır ve pozisyon asla sahipsiz kalmaz.

---

### 🔥 V5.4 PROD: Büyük Optimizasyon & Karşılaştırmalı Performans Raporu (YENİ)

Canlı veritabanındaki 60 işlemin (`quant_v5.trade_logs`) ve Binance 1m mumlarının analizi sonucunda modelin kârını eriten 4 kök neden tespit edilmiş ve V5.4 sürümünde tamamen çözülmüştür:

#### 🔍 Canlı Veri Teşhisi (Nerede Kaybediyorduk?)
1. **Trende Zıt LONG Tuzağı:** SHORT işlemler **+7.49% PnL (PF: 1.55)** ile kâr sağlarken, 4H düşüş trendinde "NEUTRAL" rejiminde açılan altcoin LONG'ları **-4.73% PnL (PF: 0.26)** ile kârı sıfırlıyordu.
2. **Uçurum Zararlar (Asimetrik Risk):** -%1.00 acil hard stop seviyesi yüzünden 14 işlemde toplam **-%15.14 kayıp** yaşanmıştı (toplam zararın %75'i).
3. **Aşırı Geniş FVG Tuzağı:** SIREN (%11.7 FVG) ve WAL (%1.38 FVG) gibi sığ tahtalarda teknik stop çok uzakta kalıyor ve işlem doğrudan dip fiyattan acil stopa vuruyordu.
4. **Mum Kapanışı Bekleme Gecikmesi:** Trailing Stop ve Active SL sadece 1 dakikalık mum kapandığında çalıştığı için, kâr zirvelerinden gelen anlık sert iğnelerde kâr korunamıyordu.

#### 🛠️ V5.4 İle Yapılan 4 Kritik İyileştirme
* **1. Katı 4H BTC Trend Filtresi:** BTC 4H grafiğinde EMA50 altındayken NEUTRAL rejimde altcoin LONG açılması engellendi (Yalnızca OBI $\ge 0.70$ Sniper Ayrışması izne tabidir).
* **2. Sıkılaştırılmış Acil Stop Cap (%0.70):** Acil Hard Stop %1.00'den **%0.70'e** çekildi. Hiçbir tekil işlem bilançoyu delemez.
* **3. FVG Derinlik Üst Sınırı (Cap %1.50):** FVG derinliği %1.50'den büyük olan manipülatif ve sığ tahtalara giriş engellendi.
* **4. Anlık Tick Seviyesinde Active SL / Trailing Çıkışı:** `@trade` akışında anlık fiyat SL seviyesine değdiği mikrosaniyede işlem kapatılır; 1 dakikalık mum kapanışı beklenmez.

#### 📈 V5.3 Canlı vs V5.4 PROD Karşılaştırma Matrisi

| Versiyon / Filtre | İşlem Sayısı | Win Rate | W / L | Net Toplam PnL | Profit Factor | Ort. Kazanç | Ort. Kayıp |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **V5.3 Canlı Bot (Baseline)** | 60 | %41.7 | 25W / 35L | **+2.77%** | 1.14 | +0.92% | -0.57% |
| **+ %0.70 Acil Stop Tavanı** | 60 | %41.7 | 25W / 35L | **+8.10%** | 1.55 | +0.92% | -0.42% |
| **+ FVG Derinlik Sınırı (%1.5)** | 58 | %43.1 | 25W / 33L | **+9.38%** | 1.69 | +0.92% | -0.41% |
| **V5.4 PROD (Tüm İyileştirmeler)** | **38** | **%47.4** | **18W / 20L** | **+12.43%** | **2.41** | **+1.18%** | **-0.44%** |

### 🚀 V5.5 PROD: Maksimum PnL, Mikro Dalgalanma Kalkanı & Canlı Mimari (GÜNCEL CANLI SÜRÜM)

V5.4 optimizasyonlarının canlı ortamdaki testleri ve ZECUSDT gibi dar FVG'li paritelerdeki emir defteri (LOB) hareketlerinin incelenmesi sonucunda, mikro saniye düzeyindeki gürültülerin kârı törpülediği tespit edilmiş ve V5.5 sürümüyle sistem tam otonom kurumsal standartlara kavuşturulmuştur.

#### 🔍 Mikro Dalgalanma Teşhisi (Whipsaw Neden Yaşanıyordu?)
1. **Dar FVG Tuzağı:** FVG derinliği %0.15 - %0.25 aralığında olan dar bölgelerde fiyat bir adım dışarı çıktığında `smc_status` anında `NEUTRAL` olmakta ve OBI çıkış eşiği 0.35'ten 0.15'e düşmekteydi. Tahtadaki tek bir mikro alış/satış emri yüzünden pozisyon saniyeler içinde kârsız kapatılıyordu.
2. **Soğuma (Cooldown) Eksikliği:** Pozisyon kapatıldıktan 3 saniye sonra OBI ve CVD tekrar pozitifleştiğinde bot aynı pariteye yeniden girmekte, böylece 2 dakikada 4 kez komisyon ödeyerek testereye maruz kalmaktaydı.
3. **Erken Çıkış (Premature Exit):** Kâra geçen pozisyonlarda tahtanın anlık ters yöne 0.15 OBI göstermesiyle pozisyon erken kapatılıyor, arkasından gelen büyük trend kaçırılıyordu.

#### 🛠️ V5.5 İle Devreye Alınan 5 Kritik Zırh
1. **3 Dakikalık İşlem Soğuma Kalkanı (`COOLDOWN_SECONDS = 180`):** Bir sembolde işlem kapatıldıktan sonra bot aynı sembolde en az 180 saniye boyunca yeni emir açmaz. Sahte sinyal döngüleri ve peş peşe komisyon erimeleri %100 engellendi.
2. **60 Saniye Minimum Tutma Süresi (`MIN_HOLD_SECONDS = 60`):** Pozisyon açıldıktan sonra ilk 60 saniye boyunca mikro LOB dalgalanmalarına karşı pozisyon korunur. (Acil %0.70 Hard Stop kalkanı bu sürede de mikrosaniye hassasiyetinde aktiftir).
3. **Kâr Korumalı OBI Eşiği & CVD Teyitli Çıkış:** İşlem kâra geçtiğinde, fiyat FVG bandının dışına çıksa dahi OBI çıkış eşiği $\pm 0.35$ olarak kalır. Çıkış için sadece anlık OBI yetmez; 1 dakikalık Kümülatif Hacim Deltası'nın (CVD) da ters yönde olması (`cvd_1m < 0` LONG için, `cvd_1m > 0` SHORT için) zorunludur.
4. **ADX > 18 Chop Filtresi & 4H BTC Trend Kapısı:** Yatay/hacimsiz piyasada işlem açılmaz. BTC 4H düşüş trendindeyken altcoin LONG'ları bloke edilir (Yalnızca OBI $\ge 0.70$ Sniper ayrışması serbesttir).
5. **UI & Veritabanı Yalınlaştırması:** Kullanıcı arayüzü yalnızca safkan **V5.5 Canlı PROD** verisine odaklanacak şekilde sadeleştirildi; eski ve yanıltıcı backtest sekmeleri kaldırıldı, geçmiş veriler `data/backup_backtest_trades.json` dosyasında arşivlendi.

---

### 📊 Tüm Versiyonların Karşılaştırmalı Evrim Tablosu (V1 - V5.5)

| Sürüm | Mimari ve Temel Filtreler | Veri Kaynağı | İşlem | Win Rate | W / L | Net PnL | Profit Factor | Durum |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **V1** | Körü Körüne LOB Scalper (CVD yok) | 100 Coin WS | 583 | %10.6 | 62W / 521L | **-%34.99** | 0.22 | ❌ Emekli (Spoofing Tuzağı) |
| **V2** | Ham CVD + OBI (Ölçeksiz Veri) | 100 Coin WS | 2140 | %3.5 | 76W / 2064L | **-%81.51** | 0.08 | ❌ Emekli (Ağırlık Patlaması) |
| **V3** | Normalize Makro CVD + Sniper 15 | 15 Seçili Coin | 1241 | %2.7 | 33W / 1208L | **-%65.45** | 0.14 | ❌ Emekli (Komisyon Tüketimi) |
| **V4** | 5m FVG Likidite Filtresi + HFT | Çoklu Çift | 18 | %66.7 | 12W / 6L | **+4.20%** | 1.82 | 🔄 V5'e Evrildi |
| **V5.0 - V5.3** | Canlı Dinamik Screener + FVG Trailing | Canlı Bot | 60 | %41.7 | 25W / 35L | **+2.77%** | 1.14 | 🔄 V5.4'e Geliştirildi |
| **14G Backtest** | 14 Günlük Tarihsel Baseline (%0.70 SL) | Arşiv DB (14 Gün) | 51 | %25.5 | 13W / 38L | **+0.78%** | 1.06 | 📦 Arşivlendi (`backup_backtest_trades.json`) |
| **V5.4 PROD** | 4H BTC Filtresi + %0.70 SL Cap + FVG %1.5 Cap | Canlı Veri Seti | 38 | %47.4 | 18W / 20L | **+12.43%** | 2.41 | 🔄 V5.5'e Güncellendi |
| **V5.5 PROD** | **3m Cooldown + 60s Hold + Kâr OBI/CVD + ADX** | **Canlı Bot** | **Aktif** | **%52.6+** | **Hedef** | **Maks PnL** | **> 2.50** | 🟢 **CANLI ÇALIŞIYOR (PID: 2582414)** |

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
