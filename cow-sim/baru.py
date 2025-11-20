import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4

# --- KONFIGURASI SIMULASI ---
DEVICE_ID = "Device-Sim-1"
RFID_TAG = "Cow-Sim-1"
# Gunakan UUID dummy untuk sapi, karena tidak terhubung ke DB nyata
DUMMY_COW_ID = str(uuid4()) 

# Periode Data Sesuai Permintaan: 30 Oktober hingga 30 November 2025
START_DATE = datetime(2025, 10, 30, 0, 0, 0)
END_DATE = datetime(2025, 11, 30, 23, 59, 59)
# Interval simulasi (misalnya: 120 detik atau 2 menit)
SIMULATION_INTERVAL_SECONDS = 2 

# Thresholds dari mqtt/client.py
SESSION_TIMEOUT_SECONDS = 60 # Sesi akan berakhir jika tidak ada konsumsi selama ini
NOISE_THRESHOLD = 0.005 # Gram
WEIGHT_START_THRESHOLD = 0.05 # Gram

# --- CLASS SIMULATOR UNTUK DATA HISTORIS ---
class CowFeedSimulator:
    def __init__(self):
        self.feed_weight = 0.0 # Gram. Pakan awal kosong.
        self.temperature = 30.0 
        self.device_ip = '192.168.1.100' 

        self.is_eating = False
        self.state_end_time = START_DATE
        self.current_base_rate = 0 # Rate dasar rata-rata (Gram/jam)
        self.last_scheduled_hour = -1

        # --- Variabel Sesi (Diambil dari ACTIVE_SESSIONS) ---
        self.active_session: Dict[str, Any] = {}
        # List untuk menyimpan Eat Session yang sudah selesai
        self.completed_sessions: List[Dict[str, Any]] = []

    # Fungsi bantu untuk simulasi
    def _get_random_base_rate(self):
        # Base rate (5-7 kg/jam, dikonversi ke gram)
        base_rate = random.uniform(5000.0, 7000.0) 
        variance = random.uniform(-1500.0, 1500.0)
        return base_rate + variance

    def _get_duration(self, current_time, min_min, max_min):
        """Mengambil durasi acak untuk transisi state, berbasis waktu simulasi."""
        return current_time + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram):
        self.feed_weight += amount_gram

    def check_schedule(self, current_time):
        """Pengecekan jadwal dan refill pakan berdasarkan waktu simulasi."""
        now_hour = current_time.hour
        
        if now_hour != self.last_scheduled_hour:
            # Contoh jam makan: 7 pagi dan 1 siang
            if now_hour == 7 or now_hour == 13: 
                amount = random.uniform(5000.0, 8000.0)
                self.refill_feed(amount)
                self.last_scheduled_hour = now_hour
            elif now_hour != self.last_scheduled_hour:
                 self.last_scheduled_hour = now_hour

    def update_cow_state(self, current_time):
        """Mengubah status sapi (makan/istirahat) berdasarkan waktu simulasi."""
        
        # Pengecekan pakan habis
        if self.feed_weight <= 0:
            self.is_eating = False
            self.feed_weight = 0
            return

        # Transisi status jika waktu sesi telah berakhir
        if current_time >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                # Sesi Makan (Durasi acak 15-30 menit)
                self.state_end_time = self._get_duration(current_time, 15, 30) 
                self.current_base_rate = self._get_random_base_rate()
            else:
                # Sesi Istirahat (Durasi acak 2-10 menit)
                self.state_end_time = self._get_duration(current_time, 2, 10) 

    def process_consumption(self, interval_seconds):
        """Proses konsumsi pakan, disesuaikan dengan interval simulasi."""
        consumed_this_interval = 0.0
        if self.is_eating and self.feed_weight > 0:
            
            # Simulasi konsumsi per interval (Jitter rate)
            dynamic_factor = random.uniform(0.5, 2.0) 
            instant_rate = self.current_base_rate * dynamic_factor
            
            # Konsumsi dalam gram/interval (rate/3600 detik * interval_seconds)
            consumed_this_interval = (instant_rate / 3600.0) * interval_seconds
            
            self.feed_weight -= consumed_this_interval
            if self.feed_weight < 0: 
                consumed_this_interval += self.feed_weight # Koreksi jika pakan habis
                self.feed_weight = 0
        
        return consumed_this_interval


    def start_new_session(self, weight: float, temp: float, timestamp: datetime):
        """Mencatat dimulainya sesi baru (in-memory)."""
        if self.active_session:
            # Jika ada sesi aktif dan RFID-nya berbeda, selesaikan sesi lama
            # Karena ini simulator 1 sapi/1 device, kita asumsikan RFID-nya selalu sama
            # Jadi, logika ini hanya dipanggil jika tidak ada sesi aktif
            pass 
        
        if weight > WEIGHT_START_THRESHOLD:
            self.active_session = {
                "session_id": str(uuid4()), # ID Sesi Baru
                "device_id": DEVICE_ID,
                "rfid_id": RFID_TAG,
                "cow_id": DUMMY_COW_ID,
                "time_start": timestamp,
                "weight_start": weight,
                "last_weight": weight,
                "last_seen": timestamp,
                "last_consumption_time": timestamp,
                "temp_sum": temp,
                "temp_count": 1
            }

    def finalize_session(self, last_weight: float, last_timestamp: datetime):
        """Menyelesaikan sesi aktif dan menyimpannya ke daftar hasil."""
        state = self.active_session.copy()
        self.active_session = {} # Hapus sesi aktif
        
        if not state:
            return
        
        avg_temp = state['temp_sum'] / state['temp_count'] if state['temp_count'] > 0 else 0.0
        
        # --- Simulasikan Prediksi Anomali (Dummy) ---
        # 10% kemungkinan anomali
        is_anomaly = random.random() < 0.1 
        anomaly_score = round(random.uniform(-1.0, 1.0), 4)

        session_to_save = {
            "session_id": state['session_id'],
            "device_id": DEVICE_ID,
            "rfid_id": RFID_TAG,
            "cow_id": DUMMY_COW_ID,
            "time_start": state['time_start'].strftime("%Y-%m-%dT%H:%M:%S+07:00"),
            "time_end": last_timestamp.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
            "weight_start": round(state['weight_start'], 2),
            "weight_end": round(last_weight, 2),
            "average_temp": round(avg_temp, 2),
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score
        }
        self.completed_sessions.append(session_to_save)

    def process_sensor_and_session(self, current_time, current_weight, current_temp, consumed_weight):
        """Menggabungkan logika process_mqtt_message dan check_session_timeouts."""
        
        state = self.active_session
        is_session_active = bool(state)
        
        # 1. Update Sesi Aktif
        if is_session_active:
            weight_diff = state['last_weight'] - current_weight
            state['last_seen'] = current_time
            
            # Jika ada konsumsi yang signifikan
            if consumed_weight > NOISE_THRESHOLD:
                state['last_consumption_time'] = current_time
            
            state['last_weight'] = current_weight
            state['temp_sum'] += current_temp
            state['temp_count'] += 1
            
            # 2. Periksa Timeout (Logika check_session_timeouts)
            timeout_threshold = timedelta(seconds=SESSION_TIMEOUT_SECONDS)
            if current_time - state['last_consumption_time'] > timeout_threshold:
                # Timeout konsumsi -> Selesaikan sesi
                self.finalize_session(current_weight, state['last_seen'])
        
        # 3. Mulai Sesi Baru
        elif self.is_eating and current_weight > WEIGHT_START_THRESHOLD:
             self.start_new_session(current_weight, current_temp, current_time)

    def get_payload(self, current_time):
        """Mengembalikan data sensor untuk output_sensor."""
        timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return {
            "ip": self.device_ip,
            "id": DEVICE_ID,
            "rfid": RFID_TAG,
            "w": round(self.feed_weight, 2), # Sisa pakan
            "temp": round(self.temperature + random.uniform(-1.0, 1.0), 2), # Suhu lingkungan + jitter
            "ts": timestamp
        }

# --- FUNGSI UTAMA GENERASI DATA ---

def generate_combined_historical_data():
    sim = CowFeedSimulator()
    historical_sensor_data = []
    current_time = START_DATE
    
    print(f"--- ⏳ Mulai Generasi Data ---")
    print(f"Dari: {START_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sampai: {END_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Interval: {SIMULATION_INTERVAL_SECONDS} detik.")
    
    total_seconds = (END_DATE - START_DATE).total_seconds()
    total_steps = int(total_seconds / SIMULATION_INTERVAL_SECONDS)
    step_count = 0
    
    # Loop Utama
    while current_time <= END_DATE:
        
        # 1. Simulasi Status Sapi (Refill & Transisi Makan/Istirahat)
        sim.check_schedule(current_time) 
        sim.update_cow_state(current_time)
        
        # 2. Proses Konsumsi Pakan
        consumed_weight = sim.process_consumption(SIMULATION_INTERVAL_SECONDS) 
        
        # 3. Ambil Payload Sensor Saat Ini
        payload = sim.get_payload(current_time)
        
        # 4. Proses Logika Sesi (Mulai, Update, Timeout/Selesai)
        # Logika sesi hanya dipicu jika sapi sedang makan atau baru selesai makan
        if sim.is_eating or consumed_weight > NOISE_THRESHOLD:
            sim.process_sensor_and_session(
                current_time, 
                payload['w'], 
                payload['temp'], 
                consumed_weight
            )
            
        # 5. Simpan Data Sensor
        # Simpan sensor hanya jika sapi sedang makan (seperti kode aslinya)
        if sim.is_eating:
            historical_sensor_data.append(payload)
        
        # 6. Majukan waktu simulasi
        current_time += timedelta(seconds=SIMULATION_INTERVAL_SECONDS)
        step_count += 1
        
        # Tampilkan progress
        if total_steps > 0 and step_count % (total_steps // 100 * 10) == 0:
             progress = (step_count / total_steps) * 100
             print(f"\r[PROGRESS] Memproses: {progress:.0f}% ({step_count}/{total_steps} steps)", end="", flush=True)

    # 7. Selesaikan Sesi yang Mungkin Masih Aktif di akhir simulasi
    if sim.active_session:
        sim.finalize_session(sim.active_session['last_weight'], sim.active_session['last_seen'])


    print("\r[PROGRESS] Memproses: 100%. Selesai!")
    
    # --- Output Sensor ---
    sensor_output_filename = "simulated_sensor_data.json"
    try:
        with open(sensor_output_filename, 'w') as f:
            json.dump(historical_sensor_data, f, indent=4)
        print(f"✅ Data Output Sensor ({len(historical_sensor_data)} catatan) berhasil disimpan ke {sensor_output_filename}")
    except Exception as e:
        print(f"❌ Gagal menyimpan data sensor: {e}")

    # --- Eat Session ---
    session_output_filename = "simulated_eat_sessions.json"
    try:
        with open(session_output_filename, 'w') as f:
            json.dump(sim.completed_sessions, f, indent=4)
        print(f"✅ Data Eat Session ({len(sim.completed_sessions)} sesi) berhasil disimpan ke {session_output_filename}")
    except Exception as e:
        print(f"❌ Gagal menyimpan data sesi makan: {e}")

if __name__ == "__main__":
    generate_combined_historical_data()