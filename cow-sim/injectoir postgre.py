import json
import random
from datetime import datetime, timedelta
import psycopg2 # Library untuk koneksi PostgreSQL
from psycopg2 import sql 
from psycopg2 import extras # Untuk menyisipkan data dalam batch

# --- KONFIGURASI SIMULASI (TETAP) ---
MQTT_TOPIC = "cattle/sensor" 
DEVICE_ID = "Device-Sim-1"
RFID_ID = "Cow-Sim-1" # Ganti RFID_TAG -> RFID_ID

# Periode Data
START_DATE = datetime(2025, 8, 31, 0, 0, 0)
END_DATE = datetime(2025, 11, 20, 23, 59, 59)
SIMULATION_INTERVAL_SECONDS = 1 

LATITUDE = -7.797
LONGITUDE = 110.370

# --- ⚙️ KONFIGURASI DATABASE POSTGRESQL ---
DB_NAME = "capstone_d06" 
DB_USER = "postgres"        
DB_PASSWORD = "12345678"    
DB_HOST = "localhost"            
DB_PORT = "5432"                 

TABLE_NAME = "output_sensor" # Nama tabel tujuan

# --- CLASS SIMULATOR UNTUK DATA HISTORIS (DIMODIFIKASI) ---
class CowFeedSimulator:
    def __init__(self):
        # Menyimpan dalam GRAM, nanti diubah ke KG saat kirim payload
        self.feed_weight_gram = 0.0 
        self.temperature_c = 30.0 # Ganti nama variable temperature
        self.device_ip = '192.168.1.100' 
        self.is_eating = False
        self.state_end_time = START_DATE
        self.current_base_rate_gram_per_hour = 0 
        self.last_scheduled_hour = -1

    def _get_local_ip(self):
        return '192.168.1.100'

    def _get_random_base_rate(self):
        # Base rate dalam gram/jam
        base_rate = random.uniform(5000.0, 7000.0) 
        variance = random.uniform(-1500.0, 1500.0)
        return base_rate + variance

    def _get_duration(self, current_time, min_min, max_min):
        return current_time + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram, current_time):
        self.feed_weight_gram += amount_gram

    def check_schedule(self, current_time):
        now_hour = current_time.hour
        
        if now_hour != self.last_scheduled_hour:
            if now_hour == 7 or now_hour == 13: 
                amount = random.uniform(5000.0, 8000.0) # Gram
                self.refill_feed(amount, current_time)
            self.last_scheduled_hour = now_hour

    def update_cow_state(self, current_time):
        if self.feed_weight_gram <= 0:
            self.is_eating = False
            self.feed_weight_gram = 0
            return

        if current_time >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                self.state_end_time = self._get_duration(current_time, 15, 30) 
                self.current_base_rate_gram_per_hour = self._get_random_base_rate()
            else:
                self.state_end_time = self._get_duration(current_time, 2, 10) 

    def process_consumption(self, interval_seconds):
        if self.is_eating and self.feed_weight_gram > 0:
            dynamic_factor = random.uniform(0.5, 2.0) 
            instant_rate = self.current_base_rate_gram_per_hour * dynamic_factor # gram/jam
            # Konsumsi dalam gram
            consumed_this_interval = (instant_rate / 3600.0) * interval_seconds
            
            self.feed_weight_gram -= consumed_this_interval
            if self.feed_weight_gram < 0: self.feed_weight_gram = 0

    def get_payload(self, current_time):
        # MENGUBAH GRAM MENJADI KILOGRAM (bagi 1000)
        # Pastikan urutan kolom SESUAI dengan urutan kolom di tabel output_sensor baru:
        # "timestamp", device_id, rfid_id, weight, temperature_c, ip
        return (
            current_time, # "timestamp" (TIMESTAMPTZ)
            DEVICE_ID,    # device_id (VARCHAR)
            RFID_ID,      # rfid_id (VARCHAR)
            round(self.feed_weight_gram / 1000.0, 3), # weight (DOUBLE PRECISION) -> dalam KG
            round(self.temperature_c, 2), # temperature_c (DOUBLE PRECISION)
            self.device_ip # ip (INET)
        )

# --- FUNGSI POSTGRESQL ---

def get_db_connection():
    """Membuat koneksi ke database PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.Error as e:
        print(f"❌ Gagal terkoneksi ke database: {e}")
        return None

def create_table_if_not_exists(conn):
    """Membuat tabel 'output_sensor' jika belum ada (sesuai skema baru)."""
    
    # PERHATIAN: Skema ini harus SAMA PERSIS dengan skema yang Anda berikan
    create_table_query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {} (
            "timestamp" TIMESTAMPTZ NOT NULL,
            device_id VARCHAR(50) REFERENCES device(device_id),
            rfid_id VARCHAR(50) REFERENCES rfid_tag(rfid_id),
            weight DOUBLE PRECISION,
            temperature_c DOUBLE PRECISION,
            ip INET
        );
    """).format(sql.Identifier(TABLE_NAME))
    
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_query)
        conn.commit()
        print(f"✅ Tabel '{TABLE_NAME}' siap digunakan.")
    except Exception as e:
        print(f"❌ Gagal membuat/cek tabel: {e}")
        conn.rollback()

def insert_data_batch(conn, data):
    """Menyisipkan data historis dalam batch (menggunakan executemany) untuk efisiensi."""
    if not data:
        print("ℹ️ Tidak ada data untuk dimasukkan.")
        return

    # ⚠️ Urutan kolom HARUS sesuai dengan urutan TUPLE di get_payload()
    columns = ['timestamp', 'device_id', 'rfid_id', 'weight', 'temperature_c', 'ip']
    
    # Placeholder yang disiapkan untuk query INSERT
    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier(TABLE_NAME),
        sql.SQL(', ').join(map(sql.Identifier, columns))
    )

    try:
        with conn.cursor() as cur:
            # Menggunakan execute_values untuk menyisipkan banyak baris sekaligus
            extras.execute_values(cur, insert_query, data)
        conn.commit()
        print(f"✅ Berhasil menyisipkan {len(data)} catatan ke tabel '{TABLE_NAME}'.")
    except Exception as e:
        print(f"❌ Gagal menyisipkan data: {e}")
        conn.rollback()


# --- FUNGSI UTAMA GENERASI DATA ---

def generate_historical_data():
    conn = get_db_connection()
    if conn is None:
        return

    create_table_if_not_exists(conn)
    
    sim = CowFeedSimulator()
    historical_data = [] # Data akan dikumpulkan di sini (dalam tuple)
    current_time = START_DATE
    
    print(f"--- ⏳ Mulai Generasi Data ---")
    print(f"Dari: {START_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sampai: {END_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Interval: {SIMULATION_INTERVAL_SECONDS} detik.")
    
    total_steps = int((END_DATE - START_DATE).total_seconds() / SIMULATION_INTERVAL_SECONDS)
    step_count = 0
    
    # Loop Utama
    while current_time <= END_DATE:
        # Perbarui status sapi, pakan, dan jadwal
        sim.check_schedule(current_time) 
        sim.update_cow_state(current_time)
        
        # Proses konsumsi pakan selama interval
        sim.process_consumption(SIMULATION_INTERVAL_SECONDS) 
        
        # Hanya simpan data jika sapi sedang MAKAN (dan ada pakan tersisa)
        if sim.is_eating and sim.feed_weight_gram > 0:
            payload = sim.get_payload(current_time)
            historical_data.append(payload)
        
        # Majukan waktu simulasi
        current_time += timedelta(seconds=SIMULATION_INTERVAL_SECONDS)
        step_count += 1
        
        # Tampilkan progress setiap 10%
        if total_steps > 0 and step_count % (total_steps // 100 * 10) == 0:
             progress = (step_count / total_steps) * 100
             print(f"\r[PROGRESS] Memproses: {progress:.0f}% ({step_count}/{total_steps} steps)", end="", flush=True)
        
        # Batasi jumlah data di memori sebelum insert ke DB (misal 50000)
        if len(historical_data) >= 50000:
            insert_data_batch(conn, historical_data)
            historical_data = [] # Reset list setelah insert

    # Insert sisa data
    if historical_data:
         insert_data_batch(conn, historical_data)

    print("\r[PROGRESS] Memproses: 100%. Selesai!")
    
    # Tutup koneksi DB
    conn.close()

if __name__ == "__main__":
    generate_historical_data()