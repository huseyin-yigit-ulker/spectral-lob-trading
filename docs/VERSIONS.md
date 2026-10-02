# Yapay Zeka Evrimi ve Versiyon Geçmişi (RL Agent)

Bu belge, otonom piyasa yapıcı/scalper yapay zeka ajanının (PPO - Proximal Policy Optimization) eğitim sürecindeki evrimini, karşılaşılan mimari hataları ve bilimsel çözümleri listeler.

---

## V1: Körü Körüne Scalper (OBI Sürümü)
* **Gözlem Matrisi (State - 4 Parametre):** `[OBI, OBI_10s, Return_1s, Spread]`
* **Eğitim Adımı:** 100,000
* **Backtest Sonucu (14 Saat):** 583 İşlem | %10.63 Win Rate | **- %34.99 PnL**
* **Teşhis:** Ajan, Kümülatif Hacim (CVD) verisine sahip olmadığı için sadece Emir Defterine (OBI) bakarak karar veriyordu. Balinaların tahtaya koyup sildiği "Spoofing" (Sahte Duvar) emirlerine inanıp sürekli yanlış işlemlere girdi.
* **Çözüm:** Ajanın gözlem matrisine gerçek piyasa hacmini (CVD) ekleme kararı alındı.

---

## V2: Hacim Zehirlenmesi (Ham CVD Sürümü)
* **Gözlem Matrisi (State - 5 Parametre):** `[OBI, OBI_60s, CVD_60s (Ham BTC Hacmi), Return_1s, Spread]`
* **Eğitim Adımı:** 2,000,000
* **Backtest Sonucu (14 Saat):** 2140 İşlem | %3.55 Win Rate | **- %81.51 PnL**
* **Teşhis:** Yapay zeka eğitiminde **Ölçeklendirilmemiş Veri (Unnormalized Feature)** felaketi yaşandı. OBI -1 ile +1 arasındayken, CVD verisi ağa +1500 veya -3000 gibi devasa rakamlarla beslendi. Bu durum Sinir Ağı ağırlıklarını (Weights) patlattı. Ajan kör oldu, `entropy_loss` tavan yaptı ve saniyede bir rastgele AL-SAT tuşlarına basan bir robota dönüştü.
* **Çözüm:** CVD verisini -1 ile +1 arasına sıkıştırmak (Normalizasyon).

---

## V3: Normalize Makro Ajan
* **Gözlem Matrisi (State - 5 Parametre):** `[OBI, OBI_60s, CVD_Ratio_60s, Return_1s, Spread]`
* **CVD_Ratio Formülü:** `(Alıcı Hacmi - Satıcı Hacmi) / (Toplam Hacim)`
* **Eğitim Adımı:** 2,000,000
* **Backtest Sonucu (14 Saat):** 1241 İşlem | %2.66 Win Rate | **- %65.45 PnL**
* **Teşhis:** Normalizasyon çok işe yaradı! `entropy_loss` -0.7'den -0.15'e inerek ajanın karar netliğini (özgüvenini) ispatladı. Toplam işlem sayısı 2140'tan 1241'e düşerek panik ataklar durduruldu. **ANCAK**, 1241 işlem yüzünden toplam bakiye sadece %0.08'lik taker komisyonlarına eridi.
Ajan neden hala çok sık fikir değiştiriyordu? Çünkü **Hafıza Kaybı (Amnesia)** yaşıyordu. Mevcut pozisyonunun ne olduğunu (Long/Short) bilmediği için, Long'dan Flat'a geçerken ödeyeceği komisyonu hesaplayamıyor, "Trend Dönüşü (Hysteresis)" yerine saniyelik scalping yapıyordu.

---

## V4: Hafızalı (Context-Aware) Ajan [AKTİF SÜRÜM]
* **Gözlem Matrisi (State - 6 Parametre):** `[OBI, OBI_60s, CVD_Ratio_60s, Return_1s, Spread, MEVCUT_POZISYON]`
* **Mimari Değişim:** `agent/environment.py` içine ajanın o anki fiziksel konumu (`position`: 1, 0, -1) 6. duyu organı olarak eklendi.
* **Beklenti:** Ajanın artık komisyon ücretlerinin farkına varması ve pozisyondayken gelen "küçük" aksi sinyalleri (gürültüyü) %0.08 komisyon ödememek için görmezden gelmesi (Stickiness/Hysteresis kazanması). İşlem sayısının kuralcı bot olan Gerçek Makro seviyelerine (~200) düşmesi bekleniyor.

---
*Geliştirme Tarihi: Ekim 2026*

### 🟢 Heuristic V3 (Sniper Mode - Altın Tahta Seçimi)
* **Problem:** 100 coinlik gece-gündüz taramasında (712 işlem) Toplam PnL'nin negatif çıkması.
* **Teşhis:** İşlemlerin %45'i BTC, ETH, BNB ve TRX'te gerçekleşti. Makas dar olsa da volatilite çok düşük olduğu için Ortalama Kâr %0.10'da kaldı. Ayriyeten STRK ve PENDLE gibi tahtalarda devasa Spoofing (sahte duvar) tuzakları botun Whipsaw yemesine (Ort. %-1.8 Zarar) neden oldu.
* **Çözüm (Sniper):** Jupyter ile PnL analizi yapılarak, kırılımların trend yarattığı (Ortalama kârın %0.50'leri aştığı ve Win Rate'in >%50 olduğu) 15 altın coin tespit edildi. un_sniper_agent.py yazılarak bot sadece bu dürüst tahtalarda işlem yapmaya programlandı.

### 🔵 Heuristic V4 (SMC + HFT Hybrid - Geliştirme Aşamasında)
* **Problem:** V3 (Sniper) dürüst tahtaları bulsa da, teknik analizi (fiyat bağlamını) tamamen görmezden geldiği için fiyatın "Boşlukta" yaptığı rastgele HFT manipülasyonlarında Whipsaw yeme riski taşıyor.
* **Mimari Değişiklik:** Sisteme 5 dakikalık (5m) Mum (Kline) verisi entegre edilerek Fair Value Gap (FVG) ve Order Block (OB) tespiti eklendi. OBI ve CVD mikro verileri, sadece fiyat bu 5m'lik Makro Likidite bölgelerine temas ettiğinde "Tetikleyici (Trigger)" olarak görev yapacak.
* **Yeni Dosya:** scripts/run_smc_agent.py (Önceki versiyonlar korunarak tamamen yeni bir branch/dosya üzerinden geliştirildi).
