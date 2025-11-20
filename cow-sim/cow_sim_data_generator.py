import json
import random
from datetime import datetime, timedelta

# --- KONFIGURASI SIMULASI ---
MQTT_TOPIC = "cattle/sensor" # Tetap digunakan untuk konteks data
DEVICE_ID = "Device-Sim-1"
RFID_TAG = "Cow-Sim-1"

# Periode Data
START_DATE = datetime(2025, 8, 31, 0, 0, 0)
END_DATE = datetime(2025, 11, 20, 23, 59, 59)
# Interval simulasi (misalnya: 120 detik atau 2 menit)
SIMULATION_INTERVAL_SECONDS = 2 

# Koordinat (Contoh: Yogyakarta) - Digunakan untuk identifikasi, suhu diabaikan
LATITUDE = -7.797
LONGITUDE = 110.370

# --- CLASS SIMULATOR UNTUK DATA HISTORIS ---
class CowFeedSimulator:
    def __init__(self):
        self.feed_weight = 0.0 # Gram. Pakan awal kosong.
        # Suhu lingkungan diatur konstan untuk simulasi historis (tidak ada API call)
        self.temperature = 30.0 
        
        # IP di-mockup karena tidak ada koneksi nyata
        self.device_ip = '192.168.1.100' 

        self.is_eating = False
        self.state_end_time = START_DATE
        self.current_base_rate = 0 # Rate dasar rata-rata (Gram/jam)
        
        self.last_scheduled_hour = -1

    # Mengganti fungsi yang menggunakan API/Socket/Threading
    def _get_local_ip(self):
        return '192.168.1.100'

    def _get_random_base_rate(self):
        # Base rate (5-7 kg/jam, dikonversi ke gram)
        base_rate = random.uniform(5000.0, 7000.0) 
        variance = random.uniform(-1500.0, 1500.0)
        return base_rate + variance

    def _get_duration(self, current_time, min_min, max_min):
        """Mengambil durasi acak untuk transisi state, berbasis waktu simulasi."""
        return current_time + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram, current_time):
        self.feed_weight += amount_gram
        # print(f"[{current_time}] 🍚 Pakan ditambahkan {amount_gram:.2f} gram. Total: {self.feed_weight:.2f} gram")

    def check_schedule(self, current_time):
        """Pengecekan jadwal dan refill pakan berdasarkan waktu simulasi."""
        now_hour = current_time.hour
        
        # Penjadwalan Refill
        if now_hour != self.last_scheduled_hour:
            # Contoh jam makan: 7 pagi dan 1 siang
            if now_hour == 7 or now_hour == 13: 
                # print(f"[{current_time}] [JADWAL] ⏰ Refill otomatis pukul {now_hour}:00.")
                amount = random.uniform(5000.0, 8000.0)
                self.refill_feed(amount, current_time) # 10kg = 10000g
                self.last_scheduled_hour = now_hour
            # Reset last_scheduled_hour setiap jam berganti
            elif now_hour != self.last_scheduled_hour:
                 self.last_scheduled_hour = now_hour

    def update_cow_state(self, current_time):
        """Mengubah status sapi (makan/istirahat) berdasarkan waktu simulasi."""
        
        # Pengecekan pakan habis
        if self.feed_weight <= 0:
            if self.is_eating:
                # print(f"[{current_time}] [SAPI] 🛑 Pakan habis. Berhenti makan.")
                pass
            self.is_eating = False
            self.feed_weight = 0
            return

        # Transisi status jika waktu sesi telah berakh ir
        if current_time >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                # Sesi Makan (Durasi acak 1-3 menit)
                self.state_end_time = self._get_duration(current_time, 15, 30) 
                self.current_base_rate = self._get_random_base_rate()
                # print(f"[{current_time}] [SAPI] 😋 MAKAN. Selesai: {self.state_end_time.strftime('%H:%M:%S')}")
            else:
                # Sesi Istirahat (Durasi acak 2-4 menit)
                self.state_end_time = self._get_duration(current_time, 2, 10) 
                # print(f"[{current_time}] [SAPI] 😴 ISTIRAHAT. Sampai: {self.state_end_time.strftime('%H:%M:%S')}")

    def process_consumption(self, interval_seconds):
        """Proses konsumsi pakan, disesuaikan dengan interval simulasi."""
        if self.is_eating and self.feed_weight > 0:
            total_consumed = 0.0
            
            # Simulasi konsumsi per interval
            # Jitter rate: Sapi makan tidak stabil
            dynamic_factor = random.uniform(0.5, 2.0) 
            instant_rate = self.current_base_rate * dynamic_factor
            
            # Konsumsi dalam gram/interval (rate/3600 detik * interval_seconds)
            consumed_this_interval = (instant_rate / 3600.0) * interval_seconds
            
            total_consumed = consumed_this_interval

            self.feed_weight -= total_consumed
            if self.feed_weight < 0: self.feed_weight = 0

    def get_payload(self, current_time):
        # Format timestamp yang benar
        timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return {
            "ip": self.device_ip,
            "id": DEVICE_ID,
            "rfid": RFID_TAG,
            "w": round(self.feed_weight, 2), # Sisa pakan
            "temp": round(self.temperature, 2), # Suhu lingkungan konstan
            "ts": timestamp
        }

# --- FUNGSI UTAMA GENERASI DATA ---

def generate_historical_data():
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
        # Perbarui status sapi, pakan, dan jadwal
        sim.check_schedule(current_time) 
        sim.update_cow_state(current_time)
        
        # Proses konsumsi pakan selama interval
        sim.process_consumption(SIMULATION_INTERVAL_SECONDS) 
        
        # Hanya simpan data jika sapi sedang MAKAN (sesuai logika kode asli)
        if sim.is_eating:
            payload = sim.get_payload(current_time)
            historical_data.append(payload)
        
        # Majukan waktu simulasi
        current_time += timedelta(seconds=SIMULATION_INTERVAL_SECONDS)
        step_count += 1
        
        # Tampilkan progress setiap 10%
        if total_steps > 0 and step_count % (total_steps // 100 * 10) == 0:
             progress = (step_count / total_steps) * 100
             print(f"\r[PROGRESS] Memproses: {progress:.0f}% ({step_count}/{total_steps} steps)", end="", flush=True)


    print("\r[PROGRESS] Memproses: 100%. Selesai!")
    print(f"Total {len(historical_data)} catatan data dihasilkan.")

    # Simpan ke file JSON
    output_filename = "cattle_feed_data.json"
    try:
        with open(output_filename, 'w') as f:
            json.dump(historical_data, f, indent=4)
        print(f"✅ Data berhasil disimpan ke {output_filename}")
    except Exception as e:
        print(f"❌ Gagal menyimpan data: {e}")

if __name__ == "__main__":
    generate_historical_data()