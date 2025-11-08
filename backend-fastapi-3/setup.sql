
-- (Hanya perlu dijalankan sekali per database)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Tabel untuk pengguna/peternak
CREATE TABLE farmer (

    farmer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(50) NOT NULL,

    email TEXT NOT NULL UNIQUE,

    password_hash TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()

);

-- Tabel untuk data sapi
CREATE TABLE cow (
    cow_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id UUID REFERENCES farmer(farmer_id),
    name VARCHAR(50),
    date_of_birth DATE,
    gender VARCHAR(10) CHECK (gender IN ('MALE', 'FEMALE'))
);

-- Tabel inventaris master untuk semua tag RFID
CREATE TABLE rfid_tag (
    rfid_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel inventaris master untuk stasiun pakan (device)
CREATE TABLE device (
    device_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'OFFLINE' CHECK (status IN ('ONLINE', 'OFFLINE', 'MAINTENANCE')),
    last_ip VARCHAR(50),
    last_seen TIMESTAMPTZ
);

-- Riwayat kehamilan per sapi
CREATE TABLE cow_pregnancy (
    cow_id UUID NOT NULL REFERENCES cow(cow_id) ON DELETE CASCADE,
    pregnancy_id SERIAL, -- ID unik per kehamilan (ke-1, ke-2, dst.)
    time_start TIMESTAMPTZ NOT NULL,
    time_end TIMESTAMPTZ DEFAULT NULL,
    PRIMARY KEY (cow_id, pregnancy_id) -- 1 sapi bisa hamil berkali-kali
);

-- Riwayat pemakaian RFID (log penugasan)
CREATE TABLE rfid_ownership (
    rfid_id VARCHAR(50) NOT NULL REFERENCES rfid_tag(rfid_id),
    time_start TIMESTAMPTZ NOT NULL,
    cow_id UUID NOT NULL REFERENCES cow(cow_id),
    time_end TIMESTAMPTZ DEFAULT NULL,
    PRIMARY KEY (rfid_id, time_start) -- 1 RFID bisa dipakai berkali-kali
);

-- Tabel untuk menyimpan hasil analisis per sesi makan
CREATE TABLE eat_session (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(50) NOT NULL REFERENCES device(device_id),
    rfid_id VARCHAR(50) NOT NULL REFERENCES rfid_tag(rfid_id),
    cow_id UUID NOT NULL REFERENCES cow(cow_id), -- Denormalisasi untuk kueri cepat
    time_start TIMESTAMPTZ NOT NULL,
    time_end TIMESTAMPTZ NOT NULL,
    weight_start DOUBLE PRECISION NOT NULL,
    weight_end DOUBLE PRECISION NOT NULL
);



-- Index untuk mempercepat pencarian dashboard
CREATE INDEX idx_eat_session_cow_time ON eat_session (cow_id, time_start DESC);
CREATE INDEX idx_eat_session_device_time ON eat_session (device_id, time_start DESC);





-- Tabel untuk menyimpan model ML yang sudah dilatih
CREATE TABLE machine_learning_model (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cow_id UUID REFERENCES cow(cow_id), -- NULL jika ini model 'UMUM'
    model_version VARCHAR(50) NOT NULL,
    model_data BYTEA NOT NULL,
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    training_data_start TIMESTAMPTZ NOT NULL,
    training_data_end TIMESTAMPTZ NOT NULL,
    metrics JSONB, -- Fleksibel untuk menyimpan {'precision': 0.8, ...}
    is_active BOOLEAN DEFAULT false
);



-- Index untuk memastikan hanya 1 model aktif per sapi
CREATE UNIQUE INDEX one_active_model_per_cow 
ON machine_learning_model (cow_id) 
WHERE is_active = true AND cow_id IS NOT NULL;

-- Index untuk memastikan hanya 1 model 'UMUM' yang aktif
CREATE UNIQUE INDEX one_active_general_model 
ON machine_learning_model (cow_id) 
WHERE is_active = true AND cow_id IS NULL;

-- Tabel penghubung untuk menandai sesi mana yang anomali
CREATE TABLE anomaly (
    model_id UUID NOT NULL REFERENCES machine_learning_model(model_id),
    session_id UUID NOT NULL REFERENCES eat_session(session_id) ON DELETE CASCADE,
    anomaly_score DOUBLE PRECISION,
	is_anomaly BOOLEAN DEFAULT false,
    PRIMARY KEY (model_id, session_id) -- 1 sesi bisa dideteksi oleh 1 model
);

-- Tabel untuk data sensor mentah bervolume tinggi
CREATE TABLE output_sensor (
    "timestamp" TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50) REFERENCES device(device_id),
    rfid_id VARCHAR(50) REFERENCES rfid_tag(rfid_id),
    weight DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION
    -- Tidak ada Primary Key untuk performa ingest (penulisan) maksimal
);

-- Perintah TimescaleDB untuk mengubahnya menjadi Hypertable
-- Partisi berdasarkan waktu (wajib) dan device_id (opsional)
-- Menggunakan 2 'space partitions' untuk device_id

SELECT create_hypertable('output_sensor', 'timestamp', 'device_id', 2);

-- Index (non-unique) untuk mempercepat kueri dashboard pada data mentah
CREATE INDEX idx_output_device_time ON output_sensor (device_id, "timestamp" DESC);
CREATE INDEX idx_output_rfid_time ON output_sensor (rfid_id, "timestamp" DESC);