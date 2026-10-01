# 🎯 Proje Yol Haritası (TODO) - HFT & Algoritmik Ticaret

## Aşama 1: Gerçek Zamanlı Mikro-Yapı Metriklerinin (RAM) İzlenmesi
Şu anki sinyal üretici, fiyat ve OBI verisini kullanıyor. Ancak zehirli tahtaları (Market Maker manipülasyonlarını) engellemek için kodun RAM (Hafıza) bloğuna şu hesaplamalar eklenecek:
- [ ] **Canlı Spread Hesaplaması:** `(Ask_0 - Bid_0) / Bid_0` formülüyle anlık makas takip edilecek.
- [ ] **OBI Titreme Hızı (Volatility):** Son 10 saniyedeki (100 tick) OBI verisinin Standart Sapması hesaplanarak, tahtadaki Spoofing (Sahte Duvar) yoğunluğu tespit edilecek.
- [ ] **Log Güncellemesi:** Yeni üretilecek `multi_signals.csv` dosyalarına `Spread_%` ve `OBI_Volatility` sütunları eklenecek.

## Aşama 2: Katman 1 (Muhafız / Risk Filtresi) Entegrasyonu
Algoritmanın sinyal üretmesinden hemen önce devreye girecek güvenlik kilitleri (Zehirli Akış Filtresi):
- [ ] `Spread > %0.05` ise işlem yapma (Gizli slippage/kayma maliyetini önle).
- [ ] `OBI_Volatility > Eşik_Değer` ise tahtayı 5 dakika kilitle (Spoofing savaşından uzak dur).
- [ ] `OBI` artarken `CVD` yatay kalıyor veya düşüyorsa eylemi sahte kabul et ve işlemi iptal et.

## Aşama 3: Tahta Seçimi (Top 10) ve Keskin Nişancı Modu
- [ ] 100 coinden toplanan yeni verilerle, Win Rate'i en yüksek ve Spread'i en düşük (En Dürüst Tahtaya sahip) 10-15 Coin seçilecek.
- [ ] Nihai bot, sadece bu 10-15 Altın Coin üzerinde `Geniş Ölü Bölge` stratejisi ile canlı (Maker limit emirleriyle) teste alınacak.

