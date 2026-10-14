import pandas as pd
from utils.database import get_supabase_conn
import sys

def main():
    conn = get_supabase_conn()
    if not conn:
        print("Baglanti kurulamadi. Lutfen .env dosyanizi kontrol edin.")
        sys.exit(1)

    try:
        query = "SELECT * FROM quant_v5.trade_logs ORDER BY zaman DESC"
        df = pd.read_sql(query, conn)
    except Exception as e:
        print(f"Tablo okunamadi: {e}")
        conn.close()
        sys.exit(1)
        
    conn.close()

    print("--- Sinyal İstatistikleri ---")
    print(f"Toplam sinyal sayısı: {len(df)}")
    
    if not df.empty:
        print("\nSinyal dağılımı:")
        print(df['sinyal'].value_counts().to_string())
        
        print("\nSembol bazlı sinyal dağılımı:")
        print(df['sembol'].value_counts().head(10).to_string())
        
        print("\nOrtalama OBI (LONG vs SHORT):")
        if '[+] AL (LONG)' in df['sinyal'].values:
            print(f"LONG: {df[df['sinyal'] == '[+] AL (LONG)']['obi'].mean():.4f}")
        if '[-] SAT (SHORT)' in df['sinyal'].values:
            print(f"SHORT: {df[df['sinyal'] == '[-] SAT (SHORT)']['obi'].mean():.4f}")

        print("\nSon 10 Sinyal:")
        print(df.head(10)[['zaman', 'sembol', 'sinyal', 'fiyat', 'obi', 'cvd', 'context']].to_string(index=False))

if __name__ == "__main__":
    main()
