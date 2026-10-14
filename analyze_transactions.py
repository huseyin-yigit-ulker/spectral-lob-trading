import pandas as pd
from utils.database import get_supabase_conn
import sys

def main():
    conn = get_supabase_conn()
    if not conn:
        print("Bağlantı hatası.")
        sys.exit(1)

    try:
        query = "SELECT * FROM quant_v5.trade_logs ORDER BY zaman ASC"
        df = pd.read_sql(query, conn)
    except Exception as e:
        print(f"Hata: {e}")
        conn.close()
        sys.exit(1)
    
    conn.close()

    if df.empty:
        print("Veri bulunamadı.")
        return

    trades = []
    
    # Her bir coin için ayrı state machine
    for symbol, group in df.groupby('sembol'):
        state = 'NO_POSITION'
        entry_price = 0
        entry_time = None
        
        for _, row in group.iterrows():
            sig = row['sinyal']
            fiyat = row['fiyat']
            zaman = row['zaman']
            
            if state == 'NO_POSITION':
                if sig == '[+] AL (LONG)':
                    state = 'IN_LONG'
                    entry_price = fiyat
                    entry_time = zaman
                elif sig == '[-] SAT (SHORT)':
                    state = 'IN_SHORT'
                    entry_price = fiyat
                    entry_time = zaman
            
            elif state == 'IN_LONG':
                if sig == '[!] BEKLE' or sig == '[-] SAT (SHORT)':
                    # Çıkış
                    pnl_pct = ((fiyat - entry_price) / entry_price) * 100
                    trades.append({
                        'sembol': symbol,
                        'tip': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': zaman,
                        'entry_price': entry_price,
                        'exit_price': fiyat,
                        'pnl_pct': pnl_pct,
                        'win': pnl_pct > 0
                    })
                    if sig == '[-] SAT (SHORT)':
                        state = 'IN_SHORT'
                        entry_price = fiyat
                        entry_time = zaman
                    else:
                        state = 'NO_POSITION'
                        
            elif state == 'IN_SHORT':
                if sig == '[!] BEKLE' or sig == '[+] AL (LONG)':
                    # Çıkış
                    pnl_pct = ((entry_price - fiyat) / entry_price) * 100
                    trades.append({
                        'sembol': symbol,
                        'tip': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': zaman,
                        'entry_price': entry_price,
                        'exit_price': fiyat,
                        'pnl_pct': pnl_pct,
                        'win': pnl_pct > 0
                    })
                    if sig == '[+] AL (LONG)':
                        state = 'IN_LONG'
                        entry_price = fiyat
                        entry_time = zaman
                    else:
                        state = 'NO_POSITION'

    trades_df = pd.DataFrame(trades)
    
    print("--- Transactional İşlem Analizi ---")
    if trades_df.empty:
        print("Henüz tamamlanmış (açılıp kapanmış) bir işlem bulunamadı.")
        return

    toplam_islem = len(trades_df)
    kazanan_islem = trades_df['win'].sum()
    basari_orani = (kazanan_islem / toplam_islem) * 100
    ortalama_pnl = trades_df['pnl_pct'].mean()
    toplam_pnl = trades_df['pnl_pct'].sum()

    print(f"Toplam İşlem: {toplam_islem}")
    print(f"Kazanan İşlem: {kazanan_islem} / {toplam_islem} (Başarı Oranı: %{basari_orani:.2f})")
    print(f"Ortalama Kar/Zarar: %{ortalama_pnl:.4f}")
    print(f"Kümülatif Kar/Zarar: %{toplam_pnl:.4f}")
    
    print("\nYön Bazlı Başarı Oranları:")
    longs = trades_df[trades_df['tip'] == 'LONG']
    if not longs.empty:
        l_win = longs['win'].sum()
        print(f"LONG İşlemler: {len(longs)} adet, Kazanan: {l_win} (Başarı Oranı: %{(l_win/len(longs)*100):.2f}, Ort. PnL: %{longs['pnl_pct'].mean():.4f})")
    
    shorts = trades_df[trades_df['tip'] == 'SHORT']
    if not shorts.empty:
        s_win = shorts['win'].sum()
        print(f"SHORT İşlemler: {len(shorts)} adet, Kazanan: {s_win} (Başarı Oranı: %{(s_win/len(shorts)*100):.2f}, Ort. PnL: %{shorts['pnl_pct'].mean():.4f})")

    print("\nSon 10 Transaction:")
    print(trades_df.tail(10)[['sembol', 'tip', 'entry_time', 'exit_time', 'pnl_pct']].to_string(index=False))

if __name__ == "__main__":
    main()
