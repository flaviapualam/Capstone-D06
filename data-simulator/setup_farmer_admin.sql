-- ============================================================================
-- Setup Data untuk Farmer Admin
-- Farmer ID: 9f9f3643-7936-401a-9071-0bef09c26dea
-- ============================================================================

-- Clean up existing simulator data
DELETE FROM output_sensor;

-- Clean up existing test data (keep admin farmer)
DELETE FROM rfid_ownership 
WHERE rfid_id IN (
    SELECT ro.rfid_id 
    FROM rfid_ownership ro
    JOIN cow c ON ro.cow_id = c.cow_id
    WHERE c.farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea'
);

DELETE FROM cow WHERE farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea';

DELETE FROM rfid_tag WHERE rfid_id IN ('8H13CJ7', '7F41TR2', '9K22PQ9');

DELETE FROM device WHERE device_id IN ('1', '2', '3');

-- ============================================================================
-- 1. Insert Devices
-- ============================================================================

INSERT INTO device (device_id, status, last_ip, last_seen) 
VALUES
    ('1', 'ONLINE', '192.168.1.100', NOW()),
    ('2', 'ONLINE', '192.168.1.101', NOW()),
    ('3', 'ONLINE', '192.168.1.102', NOW())
ON CONFLICT (device_id) DO NOTHING;

-- ============================================================================
-- 2. Insert RFID Tags (sesuai dengan setup_simulator_db.sql)
-- ============================================================================

INSERT INTO rfid_tag (rfid_id, created_at) 
VALUES
    ('8H13CJ7', '2025-09-01 00:00:00+07'),
    ('7F41TR2', '2025-09-01 00:00:00+07'),
    ('9K22PQ9', '2025-09-01 00:00:00+07')
ON CONFLICT (rfid_id) DO NOTHING;

-- ============================================================================
-- 3. Insert 3 Cows untuk Farmer Admin
-- ============================================================================

INSERT INTO cow (name, farmer_id, date_of_birth, gender)
VALUES 
    ('Cow-A', '9f9f3643-7936-401a-9071-0bef09c26dea', '2023-03-15', 'FEMALE'),
    ('Cow-B', '9f9f3643-7936-401a-9071-0bef09c26dea', '2023-05-20', 'FEMALE'),
    ('Cow-C', '9f9f3643-7936-401a-9071-0bef09c26dea', '2023-04-10', 'FEMALE');

-- ============================================================================
-- 4. Map RFID to Cows
-- ============================================================================

INSERT INTO rfid_ownership (rfid_id, cow_id, time_start)
SELECT '8H13CJ7', cow_id, '2025-09-01 00:00:00+07'
FROM cow 
WHERE name = 'Cow-A' 
AND farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea';

INSERT INTO rfid_ownership (rfid_id, cow_id, time_start)
SELECT '7F41TR2', cow_id, '2025-09-01 00:00:00+07'
FROM cow 
WHERE name = 'Cow-B' 
AND farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea';

INSERT INTO rfid_ownership (rfid_id, cow_id, time_start)
SELECT '9K22PQ9', cow_id, '2025-09-01 00:00:00+07'
FROM cow 
WHERE name = 'Cow-C' 
AND farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea';

-- ============================================================================
-- Verification
-- ============================================================================

\echo ''
\echo '================================================================================'
\echo '✓ Setup complete for Farmer Admin!'
\echo '================================================================================'
\echo ''

SELECT 
    f.name as farmer_name,
    f.email,
    COUNT(c.cow_id) as total_cows
FROM farmer f
LEFT JOIN cow c ON f.farmer_id = c.farmer_id
WHERE f.farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea'
GROUP BY f.name, f.email;

\echo ''
\echo 'Cows:'

SELECT 
    c.name as cow_name,
    c.date_of_birth,
    c.gender,
    ro.rfid_id,
    d.device_id
FROM cow c
LEFT JOIN rfid_ownership ro ON c.cow_id = ro.cow_id AND ro.time_end IS NULL
LEFT JOIN (
    VALUES ('8H13CJ7', '1'),
           ('7F41TR2', '2'),
           ('9K22PQ9', '3')
) d(rfid, device_id) ON ro.rfid_id = d.rfid
WHERE c.farmer_id = '9f9f3643-7936-401a-9071-0bef09c26dea'
ORDER BY c.name;

\echo ''
\echo '================================================================================'
\echo 'Next step: Run simulator with backfill_monthly_timescale.py'
\echo '================================================================================'
\echo ''
