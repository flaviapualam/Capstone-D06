import time
import json
import random
import threading
import sys
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

# --- KONFIGURASI ---
MQTT_BROKER = "localhost" # Broker publik untuk testing
MQTT_PORT = 1883
MQTT_TOPIC = "cattle/sensor"
DEVICE_ID = "Device-Sim-1"
RFID_TAG = "Cow-Sim-1"

class CowFeedSimulator:
    def __init__(self):
        self.feed_weight = 0.0  # Berat pakan di wadah (kg)
        self.temperature = 35.0 # Suhu awal
        
        # Status Sapi
        self.is_eating = False
        self.state_end_time = datetime.now()
        self.current_consume_rate = 0 # kg/jam
        
        # Status Jadwal
        self.last_scheduled_hour = -1

    def _get_random_consume_rate(self):
        # Rate 5 kg/hour dengan varians 2kg (Range 3 - 7 kg/hour)
        base_rate = 5.0
        variance = random.uniform(-2.0, 2.0)
        return base_rate + variance

    def _get_duration(self, min_min, max_min):
        return datetime.now() + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_kg):
        self.feed_weight += amount_kg
        print(f"\n[INFO] Pakan ditambahkan sebanyak {amount_kg} kg. Total: {self.feed_weight:.2f} kg")

    def check_schedule(self):
        # Cek jadwal makan (Jam 7-8 pagi dan jam 1-2 siang)
        now = datetime.now()
        current_hour = now.hour
        
        # Mencegah refill berulang-ulang di jam yang sama
        if current_hour != self.last_scheduled_hour:
            if current_hour == 7 or current_hour == 13: # 7 AM or 1 PM
                print(f"\n[JADWAL] Waktunya makan rutin (Pukul {current_hour}:00). Mengisi pakan...")
                self.refill_feed(10.0) # Isi 10kg otomatis
                self.last_scheduled_hour = current_hour

    def update_cow_state(self):
        now = datetime.now()
        
        # Jika pakan habis, paksa berhenti makan
        if self.feed_weight <= 0:
            self.is_eating = False
            self.feed_weight = 0
            return

        # Logika pergantian status (Makan <-> Istirahat)
        if now >= self.state_end_time:
            self.is_eating = not self.is_eating # Toggle status
            
            if self.is_eating:
                # Mulai Makan (15 - 30 menit)
                self.state_end_time = self._get_duration(15, 30)
                self.current_consume_rate = self._get_random_consume_rate()
                print(f"\n[SAPI] Mulai MAKAN. Rate: {self.current_consume_rate:.2f} kg/jam. Sampai: {self.state_end_time.strftime('%H:%M:%S')}")
            else:
                # Mulai Istirahat (2 - 10 menit)
                self.state_end_time = self._get_duration(2, 10)
                print(f"\n[SAPI] Mulai ISTIRAHAT. Sampai: {self.state_end_time.strftime('%H:%M:%S')}")

    def process_consumption(self, interval_seconds):
        if self.is_eating and self.feed_weight > 0:
            # Hitung pengurangan berat per detik
            # kg/detik = kg/jam / 3600
            loss_per_sec = self.current_consume_rate / 3600 
            consumed = loss_per_sec * interval_seconds
            
            self.feed_weight -= consumed
            if self.feed_weight < 0: self.feed_weight = 0

        # Simulasi fluktuasi suhu kecil
        self.temperature += random.uniform(-0.1, 0.1)

    def get_payload(self):
        # Format ISO 8601 dengan Timezone (disimplifikasi +07:00)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
        
        return json.dumps({
            "ip": "10.18.236.88",
            "id": DEVICE_ID,
            "rfid": RFID_TAG,
            "w": round(self.feed_weight, 2),
            "temp": round(self.temperature, 2),
            "ts": timestamp
        })

# --- MAIN PROGRAM ---

def input_listener(sim):
    """Thread untuk manual trigger refill pakan"""
    print("Ketik 'add' lalu tekan Enter untuk menambah pakan manual.")
    while True:
        user_input = input()
        if user_input.strip().lower() == "add":
            sim.refill_feed(5.0) # Tambah 5kg manual
        elif user_input.strip().lower() == "exit":
            print("Menghentikan simulasi...")
            sys.exit()

def main():
    # Setup MQTT
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Terhubung ke MQTT Broker: {MQTT_BROKER}")
    except Exception as e:
        print(f"Gagal koneksi MQTT: {e}")
        return

    sim = CowFeedSimulator()

    # Jalankan thread untuk input manual agar tidak memblokir loop utama
    input_thread = threading.Thread(target=input_listener, args=(sim,), daemon=True)
    input_thread.start()

    print("Simulasi Berjalan...")
    print("Note: Jadwal makan otomatis jam 07:00 & 13:00.")
    
    # Main Loop
    try:
        while True:
            # 1. Cek Jadwal
            sim.check_schedule()
            
            # 2. Update Status Sapi (Makan/Istirahat)
            sim.update_cow_state()
            
            # 3. Hitung Konsumsi (Simulasi per 2 detik)
            sim.process_consumption(interval_seconds=2)
            
            # 4. Kirim Data MQTT
            payload = sim.get_payload()
            client.publish(MQTT_TOPIC, payload)
            
            # Visualisasi di Terminal (Optional)
            status = "MAKAN" if sim.is_eating else "ISTIRAHAT"
            print(f"\r[{status}] Payload: {payload}", end="")
            
            time.sleep(2) # Kirim data setiap 2 detik

    except KeyboardInterrupt:
        print("\nSimulasi berhenti.")
        client.disconnect()

if __name__ == "__main__":
    main()