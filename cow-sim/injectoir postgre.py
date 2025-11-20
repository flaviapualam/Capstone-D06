# import json
# import random
# from datetime import datetime, timedelta
# import psycopg2 # Library untuk koneksi PostgreSQL
# from psycopg2 import sql 
# from psycopg2 import extras # Untuk menyisipkan data dalam batch

# # --- KONFIGURASI SIMULASI (TETAP) ---
# MQTT_TOPIC = "cattle/sensor" 
# DEVICE_ID = "Device-Sim-1"
# RFID_ID = "Cow-Sim-1" # Ganti RFID_TAG -> RFID_ID

# # Periode Data
# START_DATE = datetime(2025, 8, 17, 0, 0, 0)
# END_DATE = datetime(2025, 11, 20, 23, 59, 59)
# SIMULATION_INTERVAL_SECONDS = 1 

# LATITUDE = -7.797
# LONGITUDE = 110.370

# # --- ⚙️ KONFIGURASI DATABASE POSTGRESQL ---
# DB_NAME = "capstone_d06" 
# DB_USER = "postgres"        
# DB_PASSWORD = "12345678"    
# DB_HOST = "103.181.143.162"            
# DB_PORT = "5432"                 

# TABLE_NAME = "output_sensor" # Nama tabel tujuan

# # --- CLASS SIMULATOR UNTUK DATA HISTORIS (DIMODIFIKASI) ---
# class CowFeedSimulator:
#     def __init__(self):
#         # Menyimpan dalam GRAM, nanti diubah ke KG saat kirim payload
#         self.feed_weight_gram = 0.0 
#         self.temperature_c = 30.0 # Ganti nama variable temperature
#         self.device_ip = '192.168.1.100' 
#         self.is_eating = False
#         self.state_end_time = START_DATE
#         self.current_base_rate_gram_per_hour = 0 
#         self.last_scheduled_hour = -1

#     def _get_local_ip(self):
#         return '192.168.1.100'

#     def _get_random_base_rate(self):
#         # Base rate dalam gram/jam
#         base_rate = random.uniform(5000.0, 7000.0) 
#         variance = random.uniform(-1500.0, 1500.0)
#         return base_rate + variance

#     def _get_duration(self, current_time, min_min, max_min):
#         return current_time + timedelta(minutes=random.uniform(min_min, max_min))

#     def refill_feed(self, amount_gram, current_time):
#         self.feed_weight_gram += amount_gram

#     def check_schedule(self, current_time):
#         now_hour = current_time.hour
        
#         if now_hour != self.last_scheduled_hour:
#             if now_hour == 7 or now_hour == 13: 
#                 amount = random.uniform(5000.0, 8000.0) # Gram
#                 self.refill_feed(amount, current_time)
#             self.last_scheduled_hour = now_hour

#     def update_cow_state(self, current_time):
#         if self.feed_weight_gram <= 0:
#             self.is_eating = False
#             self.feed_weight_gram = 0
#             return

#         if current_time >= self.state_end_time:
#             self.is_eating = not self.is_eating
#             if self.is_eating:
#                 self.state_end_time = self._get_duration(current_time, 15, 30) 
#                 self.current_base_rate_gram_per_hour = self._get_random_base_rate()
#             else:
#                 self.state_end_time = self._get_duration(current_time, 2, 10) 

#     def process_consumption(self, interval_seconds):
#         if self.is_eating and self.feed_weight_gram > 0:
#             dynamic_factor = random.uniform(0.5, 2.0) 
#             instant_rate = self.current_base_rate_gram_per_hour * dynamic_factor # gram/jam
#             # Konsumsi dalam gram
#             consumed_this_interval = (instant_rate / 3600.0) * interval_seconds
            
#             self.feed_weight_gram -= consumed_this_interval
#             if self.feed_weight_gram < 0: self.feed_weight_gram = 0

#     def get_payload(self, current_time):
#         # MENGUBAH GRAM MENJADI KILOGRAM (bagi 1000)
#         # Pastikan urutan kolom SESUAI dengan urutan kolom di tabel output_sensor baru:
#         # "timestamp", device_id, rfid_id, weight, temperature_c, ip
#         return (
#             current_time, # "timestamp" (TIMESTAMPTZ)
#             DEVICE_ID,    # device_id (VARCHAR)
#             RFID_ID,      # rfid_id (VARCHAR)
#             round(self.feed_weight_gram / 1.0, 3), # weight (DOUBLE PRECISION) -> dalam gram
#             round(self.temperature_c, 2), # temperature_c (DOUBLE PRECISION)
#             self.device_ip # ip (INET)
#         )

# # --- FUNGSI POSTGRESQL ---

# def get_db_connection():
#     """Membuat koneksi ke database PostgreSQL."""
#     try:
#         conn = psycopg2.connect(
#             dbname=DB_NAME,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             host=DB_HOST,
#             port=DB_PORT
#         )
#         return conn
#     except psycopg2.Error as e:
#         print(f"❌ Gagal terkoneksi ke database: {e}")
#         return None

# def create_table_if_not_exists(conn):
#     """Membuat tabel 'output_sensor' jika belum ada (sesuai skema baru)."""
    
#     # PERHATIAN: Skema ini harus SAMA PERSIS dengan skema yang Anda berikan
#     create_table_query = sql.SQL("""
#         CREATE TABLE IF NOT EXISTS {} (
#             "timestamp" TIMESTAMPTZ NOT NULL,
#             device_id VARCHAR(50) REFERENCES device(device_id),
#             rfid_id VARCHAR(50) REFERENCES rfid_tag(rfid_id),
#             weight DOUBLE PRECISION,
#             temperature_c DOUBLE PRECISION,
#             ip INET
#         );
#     """).format(sql.Identifier(TABLE_NAME))
    
#     try:
#         with conn.cursor() as cur:
#             cur.execute(create_table_query)
#         conn.commit()
#         print(f"✅ Tabel '{TABLE_NAME}' siap digunakan.")
#     except Exception as e:
#         print(f"❌ Gagal membuat/cek tabel: {e}")
#         conn.rollback()

# def insert_data_batch(conn, data):
#     """Menyisipkan data historis dalam batch (menggunakan executemany) untuk efisiensi."""
#     if not data:
#         print("ℹ️ Tidak ada data untuk dimasukkan.")
#         return

#     # ⚠️ Urutan kolom HARUS sesuai dengan urutan TUPLE di get_payload()
#     columns = ['timestamp', 'device_id', 'rfid_id', 'weight', 'temperature_c', 'ip']
    
#     # Placeholder yang disiapkan untuk query INSERT
#     insert_query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
#         sql.Identifier(TABLE_NAME),
#         sql.SQL(', ').join(map(sql.Identifier, columns))
#     )

#     try:
#         with conn.cursor() as cur:
#             # Menggunakan execute_values untuk menyisipkan banyak baris sekaligus
#             extras.execute_values(cur, insert_query, data)
#         conn.commit()
#         print(f"✅ Berhasil menyisipkan {len(data)} catatan ke tabel '{TABLE_NAME}'.")
#     except Exception as e:
#         print(f"❌ Gagal menyisipkan data: {e}")
#         conn.rollback()


# # --- FUNGSI UTAMA GENERASI DATA ---

# def generate_historical_data():
#     conn = get_db_connection()
#     if conn is None:
#         return

#     create_table_if_not_exists(conn)
    
#     sim = CowFeedSimulator()
#     historical_data = [] # Data akan dikumpulkan di sini (dalam tuple)
#     current_time = START_DATE
    
#     print(f"--- ⏳ Mulai Generasi Data ---")
#     print(f"Dari: {START_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"Sampai: {END_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"Interval: {SIMULATION_INTERVAL_SECONDS} detik.")
    
#     total_steps = int((END_DATE - START_DATE).total_seconds() / SIMULATION_INTERVAL_SECONDS)
#     step_count = 0
    
#     # Loop Utama
#     while current_time <= END_DATE:
#         # Perbarui status sapi, pakan, dan jadwal
#         sim.check_schedule(current_time) 
#         sim.update_cow_state(current_time)
        
#         # Proses konsumsi pakan selama interval
#         sim.process_consumption(SIMULATION_INTERVAL_SECONDS) 
        
#         # Hanya simpan data jika sapi sedang MAKAN (dan ada pakan tersisa)
#         if sim.is_eating and sim.feed_weight_gram > 0:
#             payload = sim.get_payload(current_time)
#             historical_data.append(payload)
        
#         # Majukan waktu simulasi
#         current_time += timedelta(seconds=SIMULATION_INTERVAL_SECONDS)
#         step_count += 1
        
#         # Tampilkan progress setiap 10%
#         if total_steps > 0 and step_count % (total_steps // 100 * 10) == 0:
#              progress = (step_count / total_steps) * 100
#              print(f"\r[PROGRESS] Memproses: {progress:.0f}% ({step_count}/{total_steps} steps)", end="", flush=True)
        
#         # Batasi jumlah data di memori sebelum insert ke DB (misal 50000)
#         if len(historical_data) >= 50000:
#             insert_data_batch(conn, historical_data)
#             historical_data = [] # Reset list setelah insert

#     # Insert sisa data
#     if historical_data:
#          insert_data_batch(conn, historical_data)

#     print("\r[PROGRESS] Memproses: 100%. Selesai!")
    
#     # Tutup koneksi DB
#     conn.close()

# if __name__ == "__main__":
#     generate_historical_data()

import json
import random
import math # Import math untuk fungsi sinus
from datetime import datetime, timedelta
import psycopg2 # Library untuk koneksi PostgreSQL
from psycopg2 import sql 
from psycopg2 import extras # Untuk menyisipkan data dalam batch

# --- KONFIGURASI SIMULASI (TETAP) ---
MQTT_TOPIC = "cattle/sensor" 
DEVICE_ID = "Device-Sim-1"
RFID_ID = "Cow-Sim-1" 

# Periode Data
START_DATE = datetime(2025, 8, 17, 0, 0, 0)
END_DATE = datetime(2025, 11, 20, 23, 59, 59)
SIMULATION_INTERVAL_SECONDS = 1 

LATITUDE = -7.797
LONGITUDE = 110.370

# --- ⚙️ KONFIGURASI DATABASE POSTGRESQL ---
DB_NAME = "capstone_d06" 
DB_USER = "postgres"        
DB_PASSWORD = "12345678"    
DB_HOST = "103.181.143.162" # Menggunakan host yang Anda tentukan           
DB_PORT = "5432"                 

TABLE_NAME = "output_sensor" 

# --- CLASS SIMULATOR UNTUK DATA HISTORIS (DIMODIFIKASI) ---
class CowFeedSimulator:
    def __init__(self):
        self.feed_weight_gram = 0.0 
        self.temperature_c = 25.0 # Suhu awal
        self.device_ip = '192.168.1.100' 
        self.is_eating = False
        self.state_end_time = START_DATE
        self.current_base_rate_gram_per_hour = 0 
        self.last_scheduled_hour = -1

        # --- KONFIGURASI SUHU SINUSOIDAL ---
        # Suhu rata-rata harian (Midpoint)
        self.T_MID = random.uniform(25.0, 26.5) 
        # Amplitudo (Setengah dari range Min ke Max)
        # Max: 28.5-31.0, Min: 22.0-22.9
        self.T_MAX = random.uniform(28.5, 31.0)
        self.T_MIN = random.uniform(22.0, 22.9)
        self.T_AMPLITUDE = (self.T_MAX - self.T_MIN) / 2.0
        
        # Penyesuaian Midpoint agar berada di tengah Min dan Max
        # Midpoint baru: (T_MAX + T_MIN) / 2
        self.T_MID = self.T_MIN + self.T_AMPLITUDE 
        
        # Waktu Puncak Suhu (Contoh: Pukul 14:00 atau 2 sore)
        self.PEAK_HOUR = 14.0 
        # Kecepatan perubahan suhu (semakin tinggi semakin fluktuatif)
        self.TEMP_SMOOTHING_FACTOR = 0.05 

    def _get_local_ip(self):
        return '192.168.1.100'

    def _get_random_base_rate(self):
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
                amount = random.uniform(5000.0, 8000.0) 
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
            instant_rate = self.current_base_rate_gram_per_hour * dynamic_factor 
            consumed_this_interval = (instant_rate / 3600.0) * interval_seconds
            
            self.feed_weight_gram -= consumed_this_interval
            if self.feed_weight_gram < 0: self.feed_weight_gram = 0

    def _update_temperature(self, current_time):
        """Menghitung suhu saat ini menggunakan fungsi sinusoidal."""
        # Waktu dalam format 24 jam (misalnya 14.5 untuk 14:30)
        time_of_day = current_time.hour + current_time.minute / 60.0 + current_time.second / 3600.0
        
        # Hitung fase sudut (satu siklus 24 jam = 2*pi radian)
        # Menggeser fase sehingga puncak terjadi di PEAK_HOUR
        phase = 2 * math.pi * (time_of_day - self.PEAK_HOUR) / 24.0
        
        # Suhu target sinusoidal: T_MID + T_AMPLITUDE * cos(phase)
        target_temp = self.T_MID + self.T_AMPLITUDE * math.cos(phase)
        
        # Tambahkan kebisingan (noise) acak kecil untuk realisme (misal +/- 0.5 C)
        target_temp += random.uniform(-0.5, 0.5)

        # Update suhu saat ini secara bertahap (smoothing)
        # Suhu tidak langsung berubah, tapi bergerak menuju suhu target
        temp_delta = (target_temp - self.temperature_c) * self.TEMP_SMOOTHING_FACTOR
        self.temperature_c += temp_delta
        
        # Pertahankan suhu dalam batas Min dan Max
        self.temperature_c = max(self.T_MIN - 1, min(self.T_MAX + 1, self.temperature_c))

    def get_payload(self, current_time):
        # MENGUBAH GRAM MENJADI KILOGRAM (bagi 1000)
        # CATATAN: Payload Anda sebelumnya menggunakan pembagian 1.0, 
        # yang berarti data 'weight' dikirim dalam GRAM. Saya kembalikan ke GRAM (dibagi 1.0)
        # Sesuai dengan permintaan terakhir Anda, tetapi tipe kolom di DB adalah DOUBLE PRECISION,
        # KILOGRAM (bagi 1000) adalah praktik yang lebih baik untuk data sensor pakan.
        
        # Jika Anda ingin tetap di Gram: round(self.feed_weight_gram / 1.0, 3)
        # Jika Anda ingin ke Kilogram (direkomendasikan): round(self.feed_weight_gram / 1000.0, 3)
        
        # Saya asumsikan Anda ingin menggunakan Gram (sesuai kode terakhir Anda, dibagi 1.0)
        return (
            current_time, # "timestamp" (TIMESTAMPTZ)
            DEVICE_ID,    # device_id (VARCHAR)
            RFID_ID,      # rfid_id (VARCHAR)
            round(self.feed_weight_gram / 1.0, 3), # weight (DOUBLE PRECISION) -> dalam GRAM
            round(self.temperature_c, 2), # temperature_c (DOUBLE PRECISION)
            self.device_ip # ip (INET)
        )

# --- FUNGSI POSTGRESQL (TIDAK BERUBAH) ---

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

    columns = ['timestamp', 'device_id', 'rfid_id', 'weight', 'temperature_c', 'ip']
    
    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier(TABLE_NAME),
        sql.SQL(', ').join(map(sql.Identifier, columns))
    )

    try:
        with conn.cursor() as cur:
            extras.execute_values(cur, insert_query, data)
        conn.commit()
        print(f"✅ Berhasil menyisipkan {len(data)} catatan ke tabel '{TABLE_NAME}'.")
    except Exception as e:
        print(f"❌ Gagal menyisipkan data: {e}")
        conn.rollback()


# --- FUNGSI UTAMA GENERASI DATA (DIMODIFIKASI) ---

def generate_historical_data():
    conn = get_db_connection()
    if conn is None:
        return

    create_table_if_not_exists(conn)
    
    sim = CowFeedSimulator()
    historical_data = [] 
    current_time = START_DATE
    
    print(f"--- ⏳ Mulai Generasi Data ---")
    print(f"Dari: {START_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sampai: {END_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Interval: {SIMULATION_INTERVAL_SECONDS} detik.")
    
    total_steps = int((END_DATE - START_DATE).total_seconds() / SIMULATION_INTERVAL_SECONDS)
    step_count = 0
    
    # Loop Utama
    while current_time <= END_DATE:
        # Perbarui status suhu menggunakan fungsi sinusoidal
        sim._update_temperature(current_time) 
        
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
        
        # Tampilkan progress
        if total_steps > 0 and step_count % (total_steps // 100 * 10) == 0:
             progress = (step_count / total_steps) * 100
             print(f"\r[PROGRESS] Memproses: {progress:.0f}% ({step_count}/{total_steps} steps)", end="", flush=True)
        
        # Batasi jumlah data di memori sebelum insert ke DB (batching)
        if len(historical_data) >= 50000:
            insert_data_batch(conn, historical_data)
            historical_data = [] 

    # Insert sisa data
    if historical_data:
         insert_data_batch(conn, historical_data)

    print("\r[PROGRESS] Memproses: 100%. Selesai!")
    
    # Tutup koneksi DB
    conn.close()

if __name__ == "__main__":
    generate_historical_data()