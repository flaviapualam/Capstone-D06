import time
import json
import random
import threading
import sys
import requests
import socket
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

# --- KONFIGURASI ---
MQTT_BROKER = "localhost" 
MQTT_PORT = 1883
MQTT_TOPIC = "cattle/sensor"
DEVICE_ID = "Device-Sim-1"
RFID_TAG = "Cow-Sim-1"

# Koordinat (Contoh: Yogyakarta)
LATITUDE = -7.797
LONGITUDE = 110.370

# --- MQTT CALLBACKS (Untuk Debugging dan Keandalan) ---
def on_connect(client, userdata, flags, rc):
    """Dipanggil saat menerima CONNACK dari broker."""
    if rc == 0:
        print("\n[MQTT] ✅ KONEKSI BERHASIL")
    else:
        print(f"\n[MQTT] ❌ KONEKSI GAGAL dengan kode: {rc}. Mencoba reconnect...")

def on_disconnect(client, userdata, rc):
    """Dipanggil saat koneksi terputus."""
    if rc != 0:
        print(f"\n[MQTT] ⚠️ DISCONNECT tak terduga. Kode: {rc}. Paho akan mencoba reconnect.")

def on_publish(client, userdata, mid):
    """Dipanggil saat pesan telah berhasil dikirim ke broker."""
    # Opsi: Bisa di-uncomment untuk log setiap pesan, namun bisa membuat terminal ramai.
    # print(f"[MQTT] Pesan terkirim (MID: {mid})")
    pass

# --- CLASS SIMULATOR ---
class CowFeedSimulator:
    def __init__(self):
        self.feed_weight = 0.0 # Gram
        self.temperature = 30.0 
        
        self.device_ip = self._get_local_ip()
        print(f"[SYSTEM] Device IP Detected: {self.device_ip}")

        self.is_eating = False
        self.state_end_time = datetime.now()
        self.current_base_rate = 0 # Rate dasar rata-rata (Gram/jam)
        
        self.last_scheduled_hour = -1
        self.last_weather_update = datetime.min 

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def fetch_real_temperature(self):
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                real_temp = data['current_weather']['temperature']
                self.temperature = float(real_temp)
                self.last_weather_update = datetime.now()
                return True, self.temperature
            else:
                return False, None
        except Exception:
            return False, None

    def _get_random_base_rate(self):
        # Base rate (5-7 kg/jam, dikonversi ke gram)
        base_rate = random.uniform(5000.0, 7000.0) 
        variance = random.uniform(-1500.0, 1500.0)
        return base_rate + variance

    def _get_duration(self, min_min, max_min):
        return datetime.now() + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram):
        self.feed_weight += amount_gram
        print(f"\n[INFO] 🍚 Pakan ditambahkan {amount_gram:.2f} gram. Total: {self.feed_weight:.2f} gram")

    def check_schedule_and_weather(self):
        now = datetime.now()
        
        # Penjadwalan Refill
        if now.hour != self.last_scheduled_hour:
            # Contoh jam makan: 7 pagi dan 1 siang
            if now.hour == 7 or now.hour == 13: 
                print(f"\n[JADWAL] ⏰ Refill otomatis pukul {now.hour}:00.")
                amount = random.uniform(5000.0, 8000.0)
                self.refill_feed(amount) # 10kg = 10000g
                self.last_scheduled_hour = now.hour

        # Update Suhu
        time_diff = now - self.last_weather_update
        if time_diff.total_seconds() > 600: # Update setiap 10 menit
            success, temp = self.fetch_real_temperature()
            if success:
                print(f"\n[CUACA] 🌡️ Update suhu real-time: {temp}°C")

    def update_cow_state(self):
        now = datetime.now()
        
        # Pengecekan pakan habis
        if self.feed_weight <= 0:
            if self.is_eating:
                print(f"\n[SAPI] 🛑 Pakan habis. Berhenti makan.")
            self.is_eating = False
            self.feed_weight = 0
            return

        # Transisi status jika waktu sesi telah berakhir
        if now >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                # Sesi Makan (Durasi acak 1-3 menit)
                self.state_end_time = self._get_duration(15, 30) 
                self.current_base_rate = self._get_random_base_rate()
                print(f"\n[SAPI] 😋 MAKAN. Base Rate Sesi Ini: {self.current_base_rate:.2f} g/jam. Selesai: {self.state_end_time.strftime('%H:%M:%S')}")
            else:
                # Sesi Istirahat (Durasi acak 2-4 menit)
                self.state_end_time = self._get_duration(2, 10) 
                print(f"\n[SAPI] 😴 ISTIRAHAT. Sampai: {self.state_end_time.strftime('%H:%M:%S')}")

    def process_consumption(self, interval_seconds):
        if self.is_eating and self.feed_weight > 0:
            total_consumed = 0.0
            
            # Simulasi konsumsi per detik dengan variasi
            for _ in range(int(interval_seconds)):
                # Jitter rate: Sapi makan tidak stabil
                dynamic_factor = random.uniform(0.5, 2.0) 
                instant_rate = self.current_base_rate * dynamic_factor
                
                # Konsumsi dalam gram/detik (rate/3600 detik)
                consumed_this_second = instant_rate / 3600.0
                
                total_consumed += consumed_this_second

            self.feed_weight -= total_consumed
            if self.feed_weight < 0: self.feed_weight = 0

    def get_payload(self):
        # Format timestamp yang benar
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return json.dumps({
            "ip": self.device_ip,
            "id": DEVICE_ID,
            "rfid": RFID_TAG,
            "w": round(self.feed_weight, 2), # Sisa pakan
            "temp": round(self.temperature, 2), # Suhu lingkungan
            "ts": timestamp
        })

# --- MAIN LISTENER & LOOP ---

def input_listener(sim):
    print("\n--- KONTROL SIMULATOR ---")
    print("Ketik 'add' untuk nambah pakan (5-8 kg), 'exit' untuk keluar.")
    while True:
        try:
            user_input = input()
            if user_input.strip().lower() == "add":
                # Tambahkan 5000-8000 gram pakan (5-8 kg)
                amount = random.uniform(5000.0, 8000.0) 
                sim.refill_feed(amount)
            elif user_input.strip().lower() == "exit":
                print("\n[SYSTEM] Keluar dari simulasi...")
                sys.exit(0)
        except EOFError:
            # Menangani ketika input ditutup (misalnya saat di pipe)
            time.sleep(1)
        except Exception:
            # Mengabaikan error input lainnya
            pass

def main():
    client = mqtt.Client()
    
    # Setup Callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    
    try:
        # Koneksi Awal
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Penting! Mulai loop network di thread terpisah untuk penanganan reconnect.
        client.loop_start() 
        
    except Exception as e:
        print(f"[SYSTEM] Gagal koneksi MQTT: {e}. Pastikan Broker Localhost jalan.")
        return

    sim = CowFeedSimulator()
    
    print("Mengambil data suhu awal...")
    sim.fetch_real_temperature()

    # Thread untuk input user
    threading.Thread(target=input_listener, args=(sim,), daemon=True).start()

    print("\n--- SIMULASI BERJALAN ---")
    print("Interval pengiriman data: 2 detik.")
    
    try:
        # Loop utama simulasi
        while True:
            sim.check_schedule_and_weather() 
            sim.update_cow_state()
            
            # Proses konsumsi pakan selama 2 detik
            sim.process_consumption(interval_seconds=2) 
            
            payload = sim.get_payload()
            
            status = "ISTIRAHAT"
            
            # --- Kondisi: Hanya kirim data jika sapi sedang MAKAN ---
            if sim.is_eating:
                # QoS 0 (Fire and forget)
                client.publish(MQTT_TOPIC, payload) 
                status = "MAKAN"
            
            # Tampilan terminal (gunakan status koneksi MQTT untuk tampilan lebih baik)
            mqtt_status = "Tersambung" if client.is_connected() else "DISCONNECTED"
            
            print(f"\r[{status}] [MQTT: {mqtt_status}] Pakan: {sim.feed_weight:.2f}g | Temp: {sim.temperature}°C | Payload: {payload[:40]}...   ", end="", flush=True)
            
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n[SYSTEM] Stop. Membersihkan koneksi...")
    finally:
        client.loop_stop() # Hentikan thread loop
        client.disconnect()
        print("[SYSTEM] Koneksi MQTT terputus.")

if __name__ == "__main__":
    main()