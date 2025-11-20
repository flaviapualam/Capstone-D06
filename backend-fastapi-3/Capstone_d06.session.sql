-- SELECT * FROM farmer;
-- SELECT * FROM cow;
-- SELECT * FROM rfid_tag;
-- SELECT * FROM device;
-- SELECT * FROM cow_pregnancy;
-- SELECT * FROM rfid_ownership;
SELECT * FROM eat_session;
-- SELECT * FROM machine_learning_model;
-- SELECT * FROM anomaly;
-- SELECT * FROM output_sensor;

-- UPDATE farmer
-- SET email = 'warwinkblue123@gmail.com'
-- WHERE farmer_id = '238cc120-0e7e-4b00-b31e-b39588ef2573';


-- DELETE FROM eat_session;
-- DELETE FROM output_sensor;
-- DELETE FROM machine_learning_model;
-- DELETE FROM anomaly;

-- SELECT *, average_temp FROM eat_session




-- 🐂 SQL Tunggal untuk ETL output_sensor ke eat_session
DELETE FROM eat_session;
INSERT INTO eat_session (
    session_id,
    device_id,
    rfid_id,
    cow_id,
    time_start,
    time_end,
    weight_start,
    weight_end,
    average_temp
)
WITH sensor_diff AS (
    -- 1. Menghitung Perbedaan Berat dan Waktu antar Baris Berurutan
    SELECT
        "timestamp",
        device_id,
        rfid_id,
        weight,
        temperature_c,
        -- Mengambil data dari baris sebelumnya (LAG)
        LAG(weight, 1, weight) OVER (PARTITION BY device_id, rfid_id ORDER BY "timestamp") AS prev_weight,
        LAG("timestamp", 1, "timestamp") OVER (PARTITION BY device_id, rfid_id ORDER BY "timestamp") AS prev_timestamp
    FROM
        output_sensor
    -- Filter rentang waktu jika Anda ingin memproses data secara bertahap
    -- WHERE "timestamp" >= '2025-08-31 07:00:00+07' 
),
session_markers AS (
    -- 2. Menandai Konsumsi dan Menghitung Jeda Sejak Konsumsi Terakhir
    SELECT
        sd.*,
        sd.prev_weight - sd.weight AS weight_diff,
        -- Menandai konsumsi aktif (> NOISE_THRESHOLD 0.005)
        CASE WHEN (sd.prev_weight - sd.weight) > 0.005 THEN TRUE ELSE FALSE END AS is_consumption,
        
        -- Mencari Timestamp Konsumsi Terakhir sebelum baris saat ini (menggunakan MAX di Window)
        MAX(CASE WHEN (sd.prev_weight - sd.weight) > 0.005 THEN sd."timestamp" ELSE NULL END)
        OVER (
            PARTITION BY sd.device_id, sd.rfid_id 
            ORDER BY sd."timestamp" 
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS last_consumption_time
    FROM
        sensor_diff sd
    WHERE
        sd.weight IS NOT NULL 
        AND sd.rfid_id IS NOT NULL 
        AND sd.weight > 0.05 -- Filter awal sesi (WEIGHT_START_THRESHOLD)
),
session_groups AS (
    -- 3. Mengidentifikasi Awal Setiap Sesi Baru (dengan Timeout 30 detik)
    SELECT
        sm.*,
        -- Menghitung gap waktu sejak konsumsi terakhir dalam detik
        EXTRACT(EPOCH FROM (sm."timestamp" - sm.last_consumption_time)) AS consumption_gap_seconds,
        
        -- Menentukan ID Grup Sesi Baru: bertambah 1 jika terjadi Timeout (> 30s) atau ini adalah baris pertama (prev_timestamp = timestamp)
        SUM(CASE 
            WHEN EXTRACT(EPOCH FROM (sm."timestamp" - sm.last_consumption_time)) > 30 THEN 1
            WHEN sm.prev_timestamp = sm."timestamp" THEN 1 
            ELSE 0 
        END) OVER (PARTITION BY sm.device_id, sm.rfid_id ORDER BY sm."timestamp") AS session_group_id
    FROM
        session_markers sm
),
final_sessions AS (
    -- 4. Agregasi Data menjadi Satu Baris Per Sesi
    SELECT
        device_id,
        rfid_id,
        MIN("timestamp") AS time_start,
        MAX("timestamp") AS time_end,
        -- Berat awal (baris pertama sesi)
        (ARRAY_AGG(weight ORDER BY "timestamp" ASC))[1] AS weight_start,
        -- Berat akhir (baris terakhir sesi)
        (ARRAY_AGG(weight ORDER BY "timestamp" DESC))[1] AS weight_end,
        AVG(temperature_c) AS average_temp
    FROM
        session_groups
    GROUP BY
        device_id, rfid_id, session_group_id
    HAVING
        -- Pastikan terjadi konsumsi: berat awal harus lebih besar dari berat akhir
        (ARRAY_AGG(weight ORDER BY "timestamp" ASC))[1] > (ARRAY_AGG(weight ORDER BY "timestamp" DESC))[1] AND
        -- Pastikan sesi memiliki durasi minimal (misalnya > 4 detik)
        EXTRACT(EPOCH FROM (MAX("timestamp") - MIN("timestamp"))) > 4
)
-- 5. Final INSERT: Gabungkan dengan cow_id dan masukkan ke eat_session
SELECT
    gen_random_uuid(), -- session_id
    fs.device_id,
    fs.rfid_id,
    ro.cow_id, -- Dapatkan cow_id dari tabel rfid_ownership
    fs.time_start,
    fs.time_end,
    fs.weight_start,
    fs.weight_end,
    ROUND(fs.average_temp::NUMERIC, 2)
FROM
    final_sessions fs
JOIN
    rfid_ownership ro 
    ON fs.rfid_id = ro.rfid_id
WHERE
    -- Pastikan sesi makan terjadi saat RFID tersebut aktif untuk Cow tersebut
    fs.time_start >= ro.time_start AND (fs.time_end <= ro.time_end OR ro.time_end IS NULL);