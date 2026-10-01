# 🎯 Proje Yol Haritası (TODO) - HFT & Algoritmik Ticaret

## Aşama 1: Gerçek Zamanlı Mikro-Yapı Metriklerinin (RAM) İzlenmesi
Şu anki sinyal üretici fiyat ve OBI verisini kullanıyor. Ancak zehirli tahtaları engellemek için kodun RAM bloğuna şu hesaplamalar eklenecek:
- [ ] **Canlı Spread Hesaplaması:** `(Ask_0 - Bid_0) / Bid_0` formülüyle anlık makas takip edilecek.
- [ ] **OBI Titreme Hızı (Volatility):** Son 10 saniyedeki OBI Standart Sapması hesaplanacak (Spoofing/Sahte Duvar tespiti).
- [ ] **Log Güncellemesi:** Yeni üretilecek `multi_signals.csv` dosyalarına `Spread_%` ve `OBI_Volatility` eklenecek.

## Aşama 2: Katman 1 (Muhafız / Risk Filtresi) - 🔴 VERİ ODAKLI GÜNCELLEMELER
Veri analizleri sonucunda güncellenmiş Zehirli Akış ve Whipsaw kilitleri:
- [ ] **Dinamik CVD Şiddet Barajı (Yeni):** Kuru kuruya `CVD > 0` şartı yeterli değil. İşleme girmek için CVD şiddetinin çok keskin (örn: son 10 dakika ortalamasının %150'si) olması zorunlu tutulacak (Kazanan işlemlerin CVD şiddeti, kaybedenlerin 2 katıdır!).
- [ ] **Divergence (Uyumsuzluk) İptali:** `Macro_OBI` tavan yapmışken, CVD zayıf kalıyorsa (Spoofing/Tuzak alarmı) işlem başlamadan iptal edilecek.
- [ ] **Makas Engeli:** `Spread > %0.05` ise işlem yapılmayacak.

## Aşama 3: Tahta Seçimi ve Keskin Nişancı Modu (Altın 10)
- [ ] **Ağır Tahtaların (Majörlerin) Kara Listesi:** Verilerde kazanma oranı çok düşük (%11-%13) çıkan BTC, BNB, TRX, ETH gibi "Ağır/Hantal" tahtalar botun radarından çıkarılacak. Bu tahtalar komisyon erozyonu yaratıyor.
- [ ] **Volatil Mid-Cap Odaklılık:** Kazanma oranı yüksek (%50+) çıkan AVAX, SAND, APT, AAVE gibi fiyatın hızlı kayabildiği (düşük MM baskısı, yüksek retail trendi olan) coinler filtrelenip sadece bu "Dürüst" tahtalara odaklanılacak.

