-- DELETE FROM rfid_tag
-- WHERE rfid_id = 'Cow-Sim-1';

-- DELETE FROM output_sensor
-- WHERE rfid_id = 'Cow-Sim-1';

-- DELETE FROM output_sensor WHERE rfid_id = 'Cow-Sim-1';

-- INSERT INTO device (device_id, status, last_ip, last_seen)
-- VALUES ('Device-Sim-1', 'ONLINE', '192.168.1.100', '2025-11-20 23:59:59+07');
-- INSERT INTO rfid_tag (rfid_id, created_at)
-- VALUES ('Cow-Sim-1', '2025-08-01 10:00:00+07');
-- INSERT INTO rfid_ownership (cow_id, rfid_id, time_start)
-- VALUES ('e2db4e9d-f10a-4ccb-a4f4-19eb51292098', 'Cow-Sim-1', '2025-08-01 10:00:00+07');

-- SELECT * FROM rfid_tag;
-- SELECT * FROM farmer;
-- SELECT * FROM cow AS c JOIN farmer as f ON f.farmer_id = c.farmer_id; 
-- SELECT * FROM output_sensor;
-- SELECT * FROM device;
-- SELECT temperature_c FROM output_sensor WHERE rfid_id = 'Cow-Sim-1';

-- -- 🐂 SQL Tunggal untuk ETL output_sensor ke eat_session
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
    SELECT
        "timestamp",
        device_id,
        rfid_id,
        weight,
        temperature_c,
        LAG(weight, 1, weight) OVER (PARTITION BY device_id, rfid_id ORDER BY "timestamp") AS prev_weight,
        LAG("timestamp", 1, "timestamp") OVER (PARTITION BY device_id, rfid_id ORDER BY "timestamp") AS prev_timestamp
    FROM
        output_sensor
    -- Filter rentang waktu jika Anda ingin memproses data secara bertahap
    -- WHERE "timestamp" >= '2025-08-31 07:00:00+07' 
),
session_markers AS (
    SELECT
        sd.*,
        sd.prev_weight - sd.weight AS weight_diff,
        CASE WHEN (sd.prev_weight - sd.weight) > 0.005 THEN TRUE ELSE FALSE END AS is_consumption,
        
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
        AND sd.weight > 0.05
),
session_groups AS (
    SELECT
        sm.*,
        EXTRACT(EPOCH FROM (sm."timestamp" - sm.last_consumption_time)) AS consumption_gap_seconds,
        
        SUM(CASE 
            WHEN EXTRACT(EPOCH FROM (sm."timestamp" - sm.last_consumption_time)) > 60 THEN 1
            WHEN sm.prev_timestamp = sm."timestamp" THEN 1 
            ELSE 0 
        END) OVER (PARTITION BY sm.device_id, sm.rfid_id ORDER BY sm."timestamp") AS session_group_id
    FROM
        session_markers sm
),
final_sessions AS (
    SELECT
        device_id,
        rfid_id,
        MIN("timestamp") AS time_start,
        MAX("timestamp") AS time_end,
        (ARRAY_AGG(weight ORDER BY "timestamp" ASC))[1] AS weight_start,
        (ARRAY_AGG(weight ORDER BY "timestamp" DESC))[1] AS weight_end,
        AVG(temperature_c) AS average_temp
    FROM
        session_groups
    GROUP BY
        device_id, rfid_id, session_group_id
    HAVING
        (ARRAY_AGG(weight ORDER BY "timestamp" ASC))[1] > (ARRAY_AGG(weight ORDER BY "timestamp" DESC))[1] AND
        EXTRACT(EPOCH FROM (MAX("timestamp") - MIN("timestamp"))) > 4
)
SELECT
    gen_random_uuid(),
    fs.device_id,
    fs.rfid_id,
    ro.cow_id, 
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
    fs.time_start >= ro.time_start AND (fs.time_end <= ro.time_end OR ro.time_end IS NULL);

SELECT count(*) FROM eat_session;