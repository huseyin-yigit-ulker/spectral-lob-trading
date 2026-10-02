# 🎯 Kurumsal HFT & SMC Yol Haritası (V4 Mimarisi)

## Aşama 4: SMC (Smart Money Concepts) ve HFT Kesişimi (V4)
Mevcut OBI ve CVD (Mikro) verilerini körü körüne kullanmak yerine, onları 5 Dakikalık (5m) yapısal likidite alanlarında (Makro) tetikleyici olarak kullanacağız.
- [ ] **SMC Engine (5m Kline WS):** Binance `kline_5m` WebSocket'ine bağlanılıp her coin için canlı Order Block (OB) ve Fair Value Gap (FVG) bölgeleri izlenecek.
- [ ] **Filtreli Tetikleme:** OBI > 0.40 ve CVD > 0 şartları, YALNIZCA fiyat bir 5m FVG veya OB içine girdiğinde (veya likidite temizliği / Sweep yaptığında) işleme dönüşecek.
- [ ] **OBI Eğimi (Türev):** OBI'nin büyüklüğü yerine, son 10 saniyedeki hız/ivme artışına bakılarak "Agresif Niyet" tespit edilecek.

## Aşama 5: Dinamik Piyasa Tarayıcı (Screener Pipeline)
- [ ] Sabit 15'li coin listesi yerine, her 4 saatte bir piyasayı tarayıp "Makası en düşük, Hacmi/Beta'sı en yüksek" ilk 15 coini dinamik olarak bota besleyen bir Python altyapısı kurulacak.

## Aşama 6: Maker (Limit) Emir Asimetrisi & RL Risk Yöneticisi
- [ ] Sinyaller `Post Only` ve `Fill or Kill (3s)` mantığıyla Limit emir olarak gönderilecek. (Taker komisyonundan kurtulma).
- [ ] PPO (Yapay Zeka) modeli al/sat yapmak yerine; piyasanın volatilitesine bakıp Kuralcı Botun OBI "Ölü Bölge" eşiklerini (Örn: ±0.30'u ±0.45'e) dinamik olarak daraltıp genişleten bir "Üst Yönetici (Meta-Controller)" olarak eğitilecek.
