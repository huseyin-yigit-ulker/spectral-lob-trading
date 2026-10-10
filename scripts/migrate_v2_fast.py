import os
import psycopg2
from psycopg2.extras import DictCursor, execute_values
from dotenv import load_dotenv

load_dotenv()

def parse_dsn(dsn: str) -> dict:
    body = dsn.split("://", 1)[1]
    creds, hostpart = body.rsplit("@", 1)
    user, password = creds.split(":", 1)
    hostport, db = hostpart.split("/", 1)
    host, port = hostport.rsplit(":", 1)
    return {"user": user, "password": password, "host": host, "port": int(port), "dbname": db}

def get_conn(dsn: str):
    dsn = dsn.strip().strip('"').strip("'")
    dsn = dsn.replace("\ufffd", "£")
    return psycopg2.connect(**parse_dsn(dsn), connect_timeout=15)

def migrate():
    dsn_v1 = os.getenv("DB_CONNECTION_STRING_V1")
    dsn_v2 = os.getenv("DB_CONNECTION_STRING")

    print("Bağlanıyor: Kaynak Veritabanı (V1)...")
    conn_v1 = get_conn(dsn_v1)
    print("Bağlanıyor: Hedef Veritabanı (V2)...")
    conn_v2 = get_conn(dsn_v2)

    cur_v1 = conn_v1.cursor(cursor_factory=DictCursor)
    cur_v2 = conn_v2.cursor()

    print("Hedef veritabanında 'quant_v5' şeması sıfırlanıyor...")
    cur_v2.execute("DROP SCHEMA IF EXISTS quant_v5 CASCADE;")
    cur_v2.execute("CREATE SCHEMA quant_v5;")
    conn_v2.commit()

    tables = ['trade_logs', 'screener_history', 'live_metrics']
    
    for table in tables:
        print(f"\n[{table}] İşleniyor...")
        # Get table definition from v1
        cur_v1.execute(f"""
            SELECT column_name, data_type, character_maximum_length, column_default, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'quant_v5' AND table_name = '{table}'
            ORDER BY ordinal_position;
        """)
        columns = cur_v1.fetchall()
        
        if not columns:
            print(f"Uyarı: {table} kaynak veritabanında bulunamadı!")
            continue
            
        col_names = [col['column_name'] for col in columns]
        
        # CREATE TABLE
        col_defs = []
        for col in columns:
            col_name = col['column_name']
            data_type = col['data_type']
            if data_type == 'character varying' and col['character_maximum_length']:
                data_type = f"VARCHAR({col['character_maximum_length']})"
            elif data_type == 'timestamp without time zone':
                data_type = 'TIMESTAMP'
                
            nullable = "" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
            
            if col_name == 'id' and 'nextval' in str(col['column_default']):
                col_defs.append(f"{col_name} SERIAL PRIMARY KEY")
            elif col_name == 'sembol' and table == 'live_metrics':
                col_defs.append(f"{col_name} {data_type} PRIMARY KEY")
            else:
                col_defs.append(f"{col_name} {data_type} {default} {nullable}".strip())
                
        create_sql = f"CREATE TABLE IF NOT EXISTS quant_v5.{table} (\n  " + ",\n  ".join(col_defs) + "\n);"
        cur_v2.execute(create_sql)
        conn_v2.commit()
        
        # 3. Verileri Kopyala
        print(f"'{table}' verileri kopyalanıyor (BULK)...")
        cur_v1.execute(f"SELECT * FROM quant_v5.{table}")
        rows = cur_v1.fetchall()
        
        if rows:
            cols_str = ", ".join(col_names)
            insert_sql = f"INSERT INTO quant_v5.{table} ({cols_str}) VALUES %s"
            
            try:
                execute_values(cur_v2, insert_sql, rows, page_size=1000)
                conn_v2.commit()
            except Exception as e:
                print(f"Hata: {e}")
                conn_v2.rollback()
            
            # Sequence (SERIAL) güncellemesi (id'ler kaymasın diye)
            if 'id' in col_names:
                cur_v2.execute(f"SELECT setval('quant_v5.{table}_id_seq', COALESCE((SELECT MAX(id)+1 FROM quant_v5.{table}), 1), false);")
                conn_v2.commit()
                
            print(f"Toplam {len(rows)} satır başarıyla aktarıldı.")
        else:
            print("Tablo boş, veri aktarılmadı.")

    cur_v1.close()
    cur_v2.close()
    conn_v1.close()
    conn_v2.close()
    print("\n[OK] Veritabanı taşıma işlemi tamamlandı!")

if __name__ == "__main__":
    migrate()
