import pygame
import sys
import threading
import time
import json
import random
import socket
import requests
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

# --- 1. KONFIGURASI DAN GLOBAL ---
MQTT_BROKER = "103.181.143.162" 
MQTT_PORT = 1883
MQTT_TOPIC = "cattle/sensor"
DEVICE_ID = "Capstone-Demonstration-1"
RFID_TAG = "Capstone-Demonstration-1"
LATITUDE = -7.797
LONGITUDE = 110.370

# PYGAME SETUP
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pixel Ranch Real-time Simulator")

# Warna (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN_GRASS = (60, 179, 113)
BROWN_TROUGH = (139, 69, 19)
LIGHT_BLUE_SKY = (135, 206, 235)
RED_BUTTON = (200, 50, 50)
GREEN_BUTTON = (50, 200, 50)
GREY_UI = (50, 50, 50)
HEALTH_COLOR = (50, 200, 50) 
HEALTH_LOW_COLOR = (200, 50, 50) 

font_path = None 
try:
    font = pygame.font.Font(font_path, 20)
    font_small = pygame.font.Font(font_path, 16)
    font_large = pygame.font.Font(font_path, 32)
except:
    font = pygame.font.SysFont("Arial", 20, bold=True)
    font_small = pygame.font.SysFont("Arial", 16)
    font_large = pygame.font.SysFont("Arial", 32, bold=True)

# --- 2. CLASS SIMULATOR LENGKAP ---

class CowFeedSimulator:
    def __init__(self):
        self.feed_weight = 0.0 # Pakan awal diset 0 kg
        self.temperature = 30.0 
        self.device_ip = self._get_local_ip()
        self.is_eating = False
        self.state_end_time = datetime.now()
        self.current_base_rate = 0 
        self.last_scheduled_hour = -1
        self.last_weather_update = datetime.min
        self.health = 100.0 
        self.mqtt_connected = False 

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
        base_rate = random.uniform(5000.0, 7000.0) 
        variance = random.uniform(-1500.0, 1500.0)
        return base_rate + variance

    def _get_duration(self, min_min, max_min):
        return datetime.now() + timedelta(minutes=random.uniform(min_min, max_min))

    def refill_feed(self, amount_gram):
        self.feed_weight += amount_gram

    def check_schedule_and_weather(self):
        now = datetime.now()
        
        if now.hour != self.last_scheduled_hour:
            if now.hour == 7 or now.hour == 13: 
                self.last_scheduled_hour = now.hour
            elif now.hour != self.last_scheduled_hour:
                 self.last_scheduled_hour = now.hour

        time_diff = now - self.last_weather_update
        if time_diff.total_seconds() > 600: 
            self.fetch_real_temperature()

    def update_cow_state(self):
        now = datetime.now()
        
        if self.feed_weight <= 0:
            if self.is_eating:
                self.is_eating = False
            self.feed_weight = 0
            self.health = max(0, self.health - 0.1)
            return

        if now >= self.state_end_time:
            self.is_eating = not self.is_eating
            if self.is_eating:
                self.state_end_time = self._get_duration(1, 3) 
                self.current_base_rate = self._get_random_base_rate()
            else:
                self.state_end_time = self._get_duration(2, 4) 

    def process_consumption(self, interval_seconds):
        if self.is_eating and self.feed_weight > 0:
            total_consumed = 0.0
            
            for _ in range(int(interval_seconds)):
                dynamic_factor = random.uniform(0.5, 2.0) 
                instant_rate = self.current_base_rate * dynamic_factor
                consumed_this_second = instant_rate / 3600.0
                total_consumed += consumed_this_second

            self.feed_weight -= total_consumed
            if self.feed_weight < 0: self.feed_weight = 0
            
            self.health = min(100.0, self.health + 0.05)

    def get_payload(self):
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return json.dumps({
            "ip": self.device_ip,
            "id": DEVICE_ID,
            "rfid": RFID_TAG,
            "w": round(self.feed_weight, 2),
            "temp": round(self.temperature, 2),
            "ts": timestamp
        })

# --- 3. FUNGSI THREADING DAN PYGAME UTILITY ---

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        userdata['simulator'].mqtt_connected = True 
    else:
        userdata['simulator'].mqtt_connected = False

def on_disconnect(client, userdata, rc):
    userdata['simulator'].mqtt_connected = False

def on_publish(client, userdata, mid):
    pass

# --- THREAD SIMULATOR ---
def simulator_thread_function(sim):
    client = mqtt.Client(userdata={'simulator': sim}) 
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception:
        sim.mqtt_connected = False
        return

    sim.fetch_real_temperature()

    try:
        while True:
            sim.check_schedule_and_weather() 
            sim.update_cow_state()
            sim.process_consumption(interval_seconds=2) 
            
            if sim.is_eating and sim.mqtt_connected: 
                payload = sim.get_payload()
                client.publish(MQTT_TOPIC, payload)
            
            time.sleep(2)
    except:
        pass

    finally:
        client.loop_stop()
        client.disconnect()


# --- PYGAME DRAWING UTILITY ---

def draw_cow(surface, x, y, is_eating):
    """Menggambar Sapi (Gaya Pixel yang lebih rapi)"""
    BODY = (200, 200, 200) 
    SPOTS = (0, 0, 0) 
    
    # Body (Blocky)
    pygame.draw.rect(surface, BODY, (x + 5, y + 10, 50, 30))
    pygame.draw.rect(surface, SPOTS, (x + 15, y + 15, 10, 10))
    pygame.draw.rect(surface, SPOTS, (x + 35, y + 25, 8, 8))

    # Legs
    pygame.draw.rect(surface, BODY, (x + 10, y + 40, 5, 10))
    pygame.draw.rect(surface, BODY, (x + 40, y + 40, 5, 10))
    
    # Head and Snout
    if is_eating:
        head_y = y + 25
        text_y = y - 10
    else:
        head_y = y - 5
        text_y = y - 20
        
    pygame.draw.rect(surface, BODY, (x + 45, head_y, 15, 10))
    pygame.draw.rect(surface, (255, 192, 203), (x + 55, head_y + 5, 5, 3)) 

    if is_eating:
        text = font_small.render("Makan!", True, SPOTS)
        surface.blit(text, (x + 30, text_y))
    else:
        text = font_small.render("Zzz", True, SPOTS)
        surface.blit(text, (x + 30, text_y))

def draw_trough(surface, x, y, fill_percentage):
    pygame.draw.rect(surface, BROWN_TROUGH, (x, y, 100, 30))
    pygame.draw.rect(surface, (80, 40, 0), (x, y, 100, 5), 2) 
    
    fill_height = int(25 * min(1.0, fill_percentage))
    pygame.draw.rect(surface, (210, 180, 140), (x + 5, y + 25 - fill_height, 90, fill_height))
    
    text_percent = font_small.render(f"{int(min(1.0, fill_percentage)*100)}%", True, BLACK)
    surface.blit(text_percent, (x + 30, y + 5))

def draw_bar(surface, x, y, width, height, current_value, max_value, color_high, color_low):
    fill_ratio = current_value / max_value
    bar_width = int(width * fill_ratio)
    
    bar_color = color_high if current_value > (max_value * 0.3) else color_low
    
    pygame.draw.rect(surface, BLACK, (x, y, width, height), 2)
    pygame.draw.rect(surface, bar_color, (x, y, bar_width, height))

# --- CLASS GUI ELEMENT ---
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.is_hovered = False

    def draw(self, surface):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect)
        
        text_surf = font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.is_hovered and self.action:
                self.action()
                return True
        return False

# --- MAIN GAME LOOP ---
def run_game(simulator):
    clock = pygame.time.Clock()

    add_feed_button = Button(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 70, 120, 50, "Add Feed", GREEN_BUTTON, (70, 220, 70), 
                             action=lambda: simulator.refill_feed(random.uniform(5000.0, 8000.0)))
    exit_button = Button(30, SCREEN_HEIGHT - 70, 100, 50, "Exit", RED_BUTTON, (220, 70, 70), 
                         action=lambda: pygame.quit() or sys.exit())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            add_feed_button.handle_event(event)
            exit_button.handle_event(event)

        # --- DRAWING ---
        current_hour = datetime.now().hour
        if 6 <= current_hour < 18: 
            SCREEN.fill(LIGHT_BLUE_SKY)
        else: 
            SCREEN.fill((20, 20, 70))
            for _ in range(20):
                pygame.draw.circle(SCREEN, WHITE, (random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT // 2)), 1)
        
        pygame.draw.rect(SCREEN, GREEN_GRASS, (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))

        pygame.draw.rect(SCREEN, (150, 75, 0), (100, SCREEN_HEIGHT // 2 - 150, 150, 150)) 
        pygame.draw.polygon(SCREEN, (100, 50, 0), [(100, SCREEN_HEIGHT // 2 - 150), 
                                                 (250, SCREEN_HEIGHT // 2 - 150), 
                                                 (175, SCREEN_HEIGHT // 2 - 200)]) 

        cow_x, cow_y = 350, SCREEN_HEIGHT // 2 - 50
        trough_x, trough_y = cow_x + 80, cow_y + 40 
        
        draw_trough(SCREEN, trough_x, trough_y, simulator.feed_weight / 15000.0) 
        draw_cow(SCREEN, cow_x, cow_y, simulator.is_eating)

        pygame.draw.rect(SCREEN, GREY_UI, (0, 0, SCREEN_WIDTH, 40))
        pygame.draw.rect(SCREEN, GREY_UI, (0, SCREEN_HEIGHT - 100, SCREEN_WIDTH, 100))

        # --- TOP BAR INFO ---
        time_text = font.render(datetime.now().strftime("%H:%M:%S"), True, WHITE)
        SCREEN.blit(time_text, (SCREEN_WIDTH - time_text.get_width() - 20, 10))

        temp_text = font.render(f"Temp: {simulator.temperature:.1f}°C", True, WHITE)
        SCREEN.blit(temp_text, (20, 10))

        mqtt_status_color = (0, 255, 0) if simulator.mqtt_connected else (255, 0, 0)
        mqtt_status_text = font_small.render(f"MQTT: {'Connected' if simulator.mqtt_connected else 'Disconnected'}", True, mqtt_status_color)
        SCREEN.blit(mqtt_status_text, (SCREEN_WIDTH // 2 - mqtt_status_text.get_width() // 2, 10))


        # --- BOTTOM BAR INFO ---
        cow_info_text = font_large.render(f"RFID: {RFID_TAG}", True, WHITE)
        SCREEN.blit(cow_info_text, (30, SCREEN_HEIGHT - 90))

        health_label = font.render(f"Health ({simulator.health:.0f}%)", True, WHITE)
        SCREEN.blit(health_label, (180, SCREEN_HEIGHT - 90))
        draw_bar(SCREEN, 180, SCREEN_HEIGHT - 70, 150, 15, simulator.health, 100.0, HEALTH_COLOR, HEALTH_LOW_COLOR)

        feed_label = font.render(f"Feed: {simulator.feed_weight/1000:.2f} kg", True, WHITE)
        SCREEN.blit(feed_label, (380, SCREEN_HEIGHT - 90))
        
        status_text = font_large.render(f"Status: {'MAKAN' if simulator.is_eating else 'ISTIRAHAT'}", True, WHITE)
        SCREEN.blit(status_text, (380, SCREEN_HEIGHT - 55))

        add_feed_button.draw(SCREEN)
        exit_button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(30) 

    pygame.quit()
    sys.exit()

# --- 4. EKSEKUSI UTAMA ---

if __name__ == "__main__":
    
    sim_instance = CowFeedSimulator()
    
    sim_thread = threading.Thread(target=simulator_thread_function, args=(sim_instance,), daemon=True)
    sim_thread.start()
    
    try:
        run_game(sim_instance)
    except Exception as e:
        pygame.quit()
        sys.exit()