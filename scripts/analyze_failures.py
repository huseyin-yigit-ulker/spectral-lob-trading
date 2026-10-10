import pandas as pd
from utils.database import get_supabase_conn
import sys

def main():
    conn = get_supabase_conn()
    if not conn:
        print("Bağlantı hatası.")
        sys.exit(1)

    try:
        query_logs = "SELECT * FROM quant_v5.trade_logs ORDER BY zaman ASC"
        df_logs = pd.read_sql(query_logs, conn)
        
        query_screener = "SELECT * FROM quant_v5.screener_history ORDER BY zaman ASC"
        df_screener = pd.read_sql(query_screener, conn)
    except Exception as e:
        print(f"Hata: {e}")
        conn.close()
        sys.exit(1)
    
    conn.close()

    if df_logs.empty:
        print("Sinyal verisi bulunamadı.")
        return

    trades = []
    
    # 1. İşlemleri (Transactions) Çıkar
    for symbol, group in df_logs.groupby('sembol'):
        state = 'NO_POSITION'
        entry_price = 0
        entry_time = None
        entry_obi = 0
        entry_cvd = 0
        entry_fvg = 0
        
        for _, row in group.iterrows():
            sig = row['sinyal']
            fiyat = row['fiyat']
            zaman = row['zaman']
            obi = row['obi']
            cvd = row['cvd']
            fvg = row['fvg_depth']
            
            if state == 'NO_POSITION':
                if sig == '[+] AL (LONG)':
                    state = 'IN_LONG'
                    entry_price = fiyat
                    entry_time = zaman
                    entry_obi = obi
                    entry_cvd = cvd
                    entry_fvg = fvg
                elif sig == '[-] SAT (SHORT)':
                    state = 'IN_SHORT'
                    entry_price = fiyat
                    entry_time = zaman
                    entry_obi = obi
                    entry_cvd = cvd
                    entry_fvg = fvg
            
            elif state == 'IN_LONG':
                if sig == '[!] BEKLE' or sig == '[-] SAT (SHORT)':
                    pnl_pct = ((fiyat - entry_price) / entry_price) * 100
                    trades.append({
                        'sembol': symbol,
                        'tip': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': zaman,
                        'entry_price': entry_price,
                        'exit_price': fiyat,
                        'pnl_pct': pnl_pct,
                        'win': pnl_pct > 0,
                        'obi': entry_obi,
                        'cvd': entry_cvd,
                        'fvg': entry_fvg
                    })
                    if sig == '[-] SAT (SHORT)':
                        state = 'IN_SHORT'
                        entry_price = fiyat
                        entry_time = zaman
                        entry_obi = obi
                        entry_cvd = cvd
                        entry_fvg = fvg
                    else:
                        state = 'NO_POSITION'
                        
            elif state == 'IN_SHORT':
                if sig == '[!] BEKLE' or sig == '[+] AL (LONG)':
                    pnl_pct = ((entry_price - fiyat) / entry_price) * 100
                    trades.append({
                        'sembol': symbol,
                        'tip': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': zaman,
                        'entry_price': entry_price,
                        'exit_price': fiyat,
                        'pnl_pct': pnl_pct,
                        'win': pnl_pct > 0,
                        'obi': entry_obi,
                        'cvd': entry_cvd,
                        'fvg': entry_fvg
                    })
                    if sig == '[+] AL (LONG)':
                        state = 'IN_LONG'
                        entry_price = fiyat
                        entry_time = zaman
                        entry_obi = obi
                        entry_cvd = cvd
                        entry_fvg = fvg
                    else:
                        state = 'NO_POSITION'

    trades_df = pd.DataFrame(trades)
    
    if trades_df.empty:
        print("Hiç işlem bulunamadı.")
        return
        
    # 2. Screener verisi ile birleştir (Entry time'a en yakın geçmiş screener kaydı)
    df_screener['zaman'] = pd.to_datetime(df_screener['zaman'])
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    
    enriched_trades = []
    for _, t in trades_df.iterrows():
        # o coinin, işleme giriş saatinden hemen önceki son 1 saatteki screener kaydı
        past_screens = df_screener[(df_screener['sembol'] == t['sembol']) & (df_screener['zaman'] <= t['entry_time'])]
        if not past_screens.empty:
            last_sc = past_screens.iloc[-1]
            t['scr_vol'] = last_sc['hacim']
            t['scr_spread'] = last_sc['spread']
            t['scr_fvg_dist'] = last_sc['fvg_mesafe_yuzde']
            t['scr_score'] = last_sc['skor']
        else:
            t['scr_vol'] = None
            t['scr_spread'] = None
            t['scr_fvg_dist'] = None
            t['scr_score'] = None
        enriched_trades.append(t)
        
    res_df = pd.DataFrame(enriched_trades)
    
    # 3. Hatalı İşlemleri (Kaybeden) Analiz Et
    losses = res_df[res_df['win'] == False].copy()
    wins = res_df[res_df['win'] == True].copy()
    
    print(f"Toplam İşlem: {len(res_df)}")
    if len(res_df) > 0:
        first_date = res_df['entry_time'].min()
        last_date = res_df['exit_time'].max()
        days = (last_date - first_date).days
        hours = (last_date - first_date).seconds // 3600
        print(f"Veri Aralığı: {first_date.strftime('%Y-%m-%d %H:%M')} - {last_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"Süre: {days} gün, {hours} saat")
        
    print(f"Kazanan: {len(wins)}, Kaybeden: {len(losses)}\n")
    
    if len(losses) > 0:
        print("--- KAYBEDEN İŞLEMLERİN ORTALAMALARI ---")
        print(f"Ortalama OBI: {losses['obi'].mean():.4f} (Beklenen: Long için >0.25, Short için <-0.25)")
        print(f"Ortalama CVD: {losses['cvd'].mean():.2f}")
        print(f"Ortalama FVG Derinliği: %{losses['fvg'].mean():.4f}")
        if 'scr_vol' in losses.columns:
            print(f"Screener Ortalama Hacim: {losses['scr_vol'].mean():,.0f}")
            print(f"Screener Ortalama Spread: %{losses['scr_spread'].mean():.4f}")
            print(f"Screener FVG Mesafesi: %{losses['scr_fvg_dist'].mean():.4f}")
            
        # Kayıpları grupla
        losses['obi_abs'] = losses['obi'].abs()
        zayif_obi = losses[losses['obi_abs'] < 0.28]
        dar_fvg = losses[losses['fvg'] < 0.15]
        yuksek_spread = losses[losses['scr_spread'] > 0.05]
        
        print("\n--- HATALARIN TEMEL SEBEPLERİ (TEŞHİS) ---")
        print(f"1. Sınırda OBI ile girilenler (|OBI| < 0.28): {len(zayif_obi)} adet (Tepki cılız kalmış olabilir)")
        print(f"2. FVG Derinliği Çok Dar Olanlar (< %0.15): {len(dar_fvg)} adet (Stop çok yakın, noise'a kurban gitmiş)")
        print(f"3. Spreadi Yüksek Olanlar (> %0.05): {len(yuksek_spread)} adet (Slipaj ve maliyet kaynaklı zararlar)")
        
        print("\nSon 5 Kaybeden İşlem Detayı:")
        print(losses.tail(5)[['sembol', 'tip', 'obi', 'cvd', 'fvg', 'scr_spread', 'pnl_pct']].to_string(index=False))

    if len(wins) > 0:
        print("\n--- KAZANAN İŞLEMLERİN ORTALAMALARI (REFERANS İÇİN) ---")
        print(f"Ortalama OBI: {wins['obi'].mean():.4f}")
        print(f"Ortalama CVD: {wins['cvd'].mean():.2f}")
        print(f"Ortalama FVG Derinliği: %{wins['fvg'].mean():.4f}")
        if 'scr_vol' in wins.columns:
            print(f"Screener Ortalama Hacim: {wins['scr_vol'].mean():,.0f}")
            print(f"Screener Ortalama Spread: %{wins['scr_spread'].mean():.4f}")

    print("\n=======================================================")
    print("--- YENİ KURALLARLA SİMÜLASYON (BETA BACKTEST) ---")
    print("Kurallar:")
    print("1. OBI Mutlak Değeri >= 0.30")
    print("2. FVG Derinliği >= %0.20")
    print("3. Screener Hacmi >= 150 Milyon Dolar")
    
    if 'scr_vol' in res_df.columns:
        filtered_df = res_df[
            (res_df['obi'].abs() >= 0.30) &
            (res_df['fvg'] >= 0.20) &
            (res_df['scr_vol'] >= 150000000)
        ]
        
        sim_wins = filtered_df[filtered_df['win'] == True]
        sim_losses = filtered_df[filtered_df['win'] == False]
        
        print(f"\nFiltre Sonrası Toplam İşlem: {len(filtered_df)}")
        if len(filtered_df) > 0:
            print(f"Kazanan: {len(sim_wins)}")
            print(f"Kaybeden: {len(sim_losses)}")
            win_rate = (len(sim_wins) / len(filtered_df)) * 100
            print(f"Yeni Win Rate: %{win_rate:.2f}")
            
            total_pnl = filtered_df['pnl_pct'].sum()
            print(f"Net Kümülatif PnL: %{total_pnl:.2f}\n")
            
            print("--- AÇILAN İŞLEMLER (YENİ KURALLARI GEÇENLER) ---")
            print(filtered_df[['sembol', 'tip', 'entry_time', 'obi', 'fvg', 'scr_vol', 'pnl_pct']].to_string(index=False))
            
            skipped_df = res_df[~res_df.index.isin(filtered_df.index)]
            skipped_wins = skipped_df[skipped_df['win'] == True]
            skipped_losses = skipped_df[skipped_df['win'] == False]
            
            print(f"\n--- AÇILMAYAN İŞLEMLER (İPTAL EDİLENLER: {len(skipped_df)}) ---")
            print(f"Önlenen Zararlı İşlem Sayısı: {len(skipped_losses)}")
            print(f"Kaçırılan Kârlı İşlem Sayısı: {len(skipped_wins)}\n")
            
            print("Kaçırılan Bazı Kârlı İşlemler (Neden açılmadı?):")
            print(skipped_wins.head(5)[['sembol', 'tip', 'obi', 'fvg', 'scr_vol', 'pnl_pct']].to_string(index=False))
            
            print("\nÖnlenen Bazı Zararlı İşlemler (İyi ki açılmamış!):")
            print(skipped_losses.head(5)[['sembol', 'tip', 'obi', 'fvg', 'scr_vol', 'pnl_pct']].to_string(index=False))
            
        else:
            print("Bu katı kurallara uyan geçmiş işlem bulunamadı.")
    else:
        print("Screener verisi eksik olduğu için tam simülasyon yapılamıyor.")
        
if __name__ == "__main__":
    main()
