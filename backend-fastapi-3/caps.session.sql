-- SELECT * FROM farmer;
-- SELECT * FROM cow;
-- SELECT * FROM cow_pregnancy;
-- SELECT * FROM rfid_tag;
-- SELECT * FROM rfid_ownership;
-- SELECT * from device;
-- SELECT * FROM output_sensor;
-- SELECT * FROM eat_session;
SELECT * FROM anomaly
-- SELECT
--     c.cow_id,
--     c.name AS cow_name,
--     r.rfid_id
-- FROM
--     cow c
-- LEFT JOIN
--     rfid_ownership r ON c.cow_id = r.cow_id AND r.time_end IS NULL;
    

-- SELECT r.rfid_id
-- FROM rfid_tag r
-- LEFT JOIN rfid_ownership o 
--        ON r.rfid_id = o.rfid_id
-- WHERE o.rfid_id IS NULL;
