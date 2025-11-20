import json
import random
from datetime import datetime, timedelta
import time # Untuk loop game sederhana

# --- KONFIGURASI GAME ---
SIMULATION_SPEED_FACTOR = 3600 # 1 detik nyata = 1 jam simulasi (3600 detik)
INITIAL_FUNDS = 5000
FEED_COST_PER_KG = 5.0 

# --- CLASS SIMULATOR (DIADAPTASI) ---

class CowFeedSimulator:
    # ... (Semua metode dari kode asli Anda dipertahankan,
    #     seperti _get_local_ip, _get_random_base_rate, _get_duration) ...
    #
    # Catatan: Kita hanya mengubah cara `refill_feed` dipanggil
    
    def __init__(self, rfid_tag="Cow-Sim-1"):
        self.rfid_tag = rfid_tag
        self.feed_weight = 5000.0 # Pakan awal 5kg
        self.temperature = 30.0 
        self.device_ip = '192.168.1.100' 
        self.is_eating = False
        self.state_end_time = datetime.now() # Akan diatur saat start
        self.current_base_rate = 0 
        self.last_scheduled_hour = -1
        self.health = 100.0 # Statistik baru: Kesehatan Sapi (0-100)
        self.last_eating_time = datetime.now()
        
    def _get_random_base_rate(self):
        # Base rate (5-7 kg/jam, dikonversi ke gram)
        base_rate = random.uniform(5000.0, 7000.0) 
        variance = random.uniform(-1500.0, 1500.0)
        return base_rate + variance
        
    def _get_duration(self, current_time, min_min, max_min):
        """Mengambil durasi acak untuk transisi state, berbasis waktu simulasi."""
        return current_time + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram):
        """Metode refill yang dipanggil oleh GameManager."""
        self.feed_weight += amount_gram
        
    def update_cow_state(self, current_time):
        """Mengubah status sapi dan mengatur waktu sesi berikutnya."""
        
        # Penalti kesehatan jika kelaparan
        if self.feed_weight <= 0:
            if self.is_eating:
                self.is_eating = False
            self.feed_weight = 0
            self.health = max(0, self.health - 0.05) # Penalti kesehatan kecil
            return

        # Transisi status jika waktu sesi telah berakhir
        if current_time >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                # Sesi Makan (15-30 menit)
                self.state_end_time = self._get_duration(current_time, 15, 30) 
                self.current_base_rate = self._get_random_base_rate()
            else:
                # Sesi Istirahat (2-10 menit)
                self.state_end_time = self._get_duration(current_time, 2, 10) 

    def process_consumption(self, interval_seconds):
        """Proses konsumsi pakan dan update kesehatan/status."""
        
        if self.is_eating and self.feed_weight > 0:
            # Jitter rate: Sapi makan tidak stabil
            dynamic_factor = random.uniform(0.5, 2.0) 
            instant_rate = self.current_base_rate * dynamic_factor
            
            # Konsumsi dalam gram/interval
            consumed_this_interval = (instant_rate / 3600.0) * interval_seconds
            
            self.feed_weight -= consumed_this_interval
            if self.feed_weight < 0: 
                self.feed_weight = 0
                self.is_eating = False # Berhenti makan jika habis
                
            # Reward kesehatan saat makan
            self.health = min(100.0, self.health + 0.01)
            self.last_eating_time = datetime.now()


class GameManager:
    def __init__(self):
        self.simulation_time = datetime(2025, 11, 20, 8, 0, 0) # Waktu mulai game
        self.cows = [CowFeedSimulator(rfid) for rfid in ["Cow-1", "Cow-2"]]
        self.funds = INITIAL_FUNDS
        self.game_running = True

    def buy_feed(self, amount_kg):
        """Aksi pemain: Beli pakan."""
        cost = amount_kg * FEED_COST_PER_KG
        if self.funds >= cost:
            self.funds -= cost
            print(f"💰 Beli pakan: {amount_kg} kg. Biaya: ${cost:.2f}")
            return amount_kg * 1000 # Mengembalikan jumlah dalam gram
        else:
            print("❌ Uang tidak cukup untuk membeli pakan!")
            return 0

    def manual_refill(self, cow_index, amount_gram):
        """Aksi pemain: Mengisi pakan secara manual ke tempat makan sapi."""
        if cow_index < len(self.cows):
            self.cows[cow_index].refill_feed(amount_gram)
            print(f"🍚 Refill {amount_gram/1000:.2f} kg pakan untuk Sapi {cow_index+1}")
        
    def check_schedule_and_refill(self):
        """Refill pakan berdasarkan jadwal (bisa dihilangkan untuk kontrol penuh pemain)."""
        # Dalam game, aksi ini biasanya dilakukan oleh pemain atau di-upgrade
        pass

    def update_game_state(self, time_step_seconds):
        """Memperbarui semua logika game per langkah waktu."""
        
        # 1. Update Waktu Simulasi
        self.simulation_time += timedelta(seconds=time_step_seconds)
        
        # 2. Update Sapi
        for cow in self.cows:
            # check_schedule_and_refill() (Dihapus/diubah agar pemain mengontrol)
            cow.update_cow_state(self.simulation_time)
            cow.process_consumption(time_step_seconds)
            
        # 3. Statistik Game (misalnya, Jual Produk)
        # Sederhana: Dapatkan penghasilan berdasarkan kesehatan sapi setiap 24 jam.
        if self.simulation_time.hour == 12 and self.simulation_time.minute == 0:
            avg_health = sum(cow.health for cow in self.cows) / len(self.cows)
            daily_income = avg_health * 5 # Penghasilan berbasis kesehatan
            self.funds += daily_income
            print(f"💸 Penghasilan harian: ${daily_income:.2f} (Kesehatan Rata-rata: {avg_health:.1f}%)")

    def run_game_loop(self):
        """Loop utama yang akan diintegrasikan ke GUI."""
        print(f"--- 🎮 FarmFeed Tycoon Mulai! ---")
        print(f"Waktu Mulai: {self.simulation_time.strftime('%Y-%m-%d %H:%M:%S')}")

        while self.game_running:
            # Waktu simulasi yang berlalu dalam satu langkah
            time_step = SIMULATION_SPEED_FACTOR 
            
            self.update_game_state(time_step)
            
            # Contoh tampilan konsol (Digantikan oleh GUI)
            print(f"\r[SIM TIME: {self.simulation_time.strftime('%H:%M:%S')} | FUNDS: ${self.funds:.2f}] ", end="")
            for i, cow in enumerate(self.cows):
                 status = "Makan" if cow.is_eating else "Istirahat"
                 print(f"| Cow {i+1}: Pakan={cow.feed_weight/1000:.2f}kg, Health={cow.health:.0f}%, Status={status}", end="")
            
            # Jeda dunia nyata
            time.sleep(1) 
            
            # Logika berhenti (untuk simulasi sederhana)
            # if self.simulation_time.day > 21: self.game_running = False 

# Jika diintegrasikan ke GUI, fungsi `run_game_loop` akan digantikan
# dengan fungsi yang dipanggil oleh timer GUI (misalnya setiap 100ms).
# if __name__ == "__main__":
#     game = GameManager()
#     game.run_game_loop()