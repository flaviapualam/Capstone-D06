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

class CowFeedSimulator:
    def __init__(self):
        self.feed_weight = 0.0 # Sekarang dalam GRAM
        self.temperature = 30.0 
        
        self.device_ip = self._get_local_ip()
        print(f"[SYSTEM] Device IP Detected: {self.device_ip}")

        self.is_eating = False
        self.state_end_time = datetime.now()
        self.current_consume_rate = 0 # Gram per jam
        
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

    def _get_random_consume_rate(self):
        # UBAH KE GRAM: 5 kg = 5000 gram
        # Varians 2 kg = 2000 gram
        base_rate = 5000.0
        variance = random.uniform(-2000.0, 2000.0)
        return base_rate + variance

    def _get_duration(self, min_min, max_min):
        return datetime.now() + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram):
        self.feed_weight += amount_gram
        # Print satuan gram
        print(f"\n[INFO] Pakan ditambahkan {amount_gram:.2f} gram. Total: {self.feed_weight:.2f} gram")

    def check_schedule_and_weather(self):
        now = datetime.now()
        
        if now.hour != self.last_scheduled_hour:
            if now.hour == 7 or now.hour == 13:
                print(f"\n[JADWAL] Refill otomatis pukul {now.hour}:00.")
                # UBAH KE GRAM: 10 kg = 10000 gram
                self.refill_feed(10000.0) 
                self.last_scheduled_hour = now.hour

        time_diff = now - self.last_weather_update
        if time_diff.total_seconds() > 600: 
            success, temp = self.fetch_real_temperature()
            if success:
                print(f"\n[CUACA] Update suhu real-time: {temp}°C")

    def update_cow_state(self):
        now = datetime.now()
        if self.feed_weight <= 0:
            self.is_eating = False
            self.feed_weight = 0
            return

        if now >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                self.state_end_time = self._get_duration(15, 30)
                self.current_consume_rate = self._get_random_consume_rate()
                # Print satuan gram/jam
                print(f"\n[SAPI] MAKAN. Rate: {self.current_consume_rate:.2f} g/jam. Sampai: {self.state_end_time.strftime('%H:%M:%S')}")
            else:
                self.state_end_time = self._get_duration(2, 10)
                print(f"\n[SAPI] ISTIRAHAT. Sampai: {self.state_end_time.strftime('%H:%M:%S')}")

    def process_consumption(self, interval_seconds):
        if self.is_eating and self.feed_weight > 0:
            loss_per_sec = self.current_consume_rate / 3600 
            consumed = loss_per_sec * interval_seconds
            self.feed_weight -= consumed
            if self.feed_weight < 0: self.feed_weight = 0

    def get_payload(self):
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return json.dumps({
            "ip": self.device_ip,
            "id": DEVICE_ID,
            "rfid": RFID_TAG,
            "w": round(self.feed_weight, 2), # Nilai w sekarang dalam GRAM
            "temp": round(self.temperature, 2),
            "ts": timestamp
        })

# --- MAIN LISTENER & LOOP ---

def input_listener(sim):
    print("Ketik 'add' untuk nambah pakan (5000-8000 gram), 'exit' untuk keluar.")
    while True:
        user_input = input()
        if user_input.strip().lower() == "add":
            # UBAH KE GRAM: 5kg - 8kg = 5000g - 8000g
            amount = random.uniform(5000.0, 8000.0)
            sim.refill_feed(amount)
        elif user_input.strip().lower() == "exit":
            sys.exit()

def main():
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Terhubung ke Broker: {MQTT_BROKER}")
    except:
        print("Gagal koneksi MQTT (Pastikan Broker Localhost jalan).")
        return

    sim = CowFeedSimulator()
    
    print("Mengambil data suhu awal...")
    sim.fetch_real_temperature()

    threading.Thread(target=input_listener, args=(sim,), daemon=True).start()

    print("Simulasi Berjalan (Satuan: Gram)...")
    
    try:
        while True:
            sim.check_schedule_and_weather() 
            sim.update_cow_state()
            sim.process_consumption(2)
            
            payload = sim.get_payload()
            client.publish(MQTT_TOPIC, payload)
            
            status = "MAKAN" if sim.is_eating else "ISTIRAHAT"
            print(f"\r[{status}] IP: {sim.device_ip} | Temp: {sim.temperature}°C | Payload: {payload}   ", end="")
            
            time.sleep(2)

    except KeyboardInterrupt:
        client.disconnect()
        print("\nStop.")

if __name__ == "__main__":
    main()