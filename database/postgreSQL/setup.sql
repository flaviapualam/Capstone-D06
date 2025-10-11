CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE farmer (
    farmer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    email VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT
);

CREATE TABLE cow (
    cow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farmer_id UUID REFERENCES farmer(farmer_id) ON DELETE CASCADE,
    name VARCHAR(50),
    age INT,
    status INT
);

CREATE TABLE ai_model (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cow_id UUID REFERENCES cow(cow_id) ON DELETE CASCADE,
    model BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sensor (
    sensor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status INT
);

CREATE TABLE clean_data (
    time_generated TIMESTAMP NOT NULL,
    cow_id UUID NOT NULL,
    sensor_id UUID NOT NULL,
    eat_duration INT,
    eat_speed INT,
    anomaly_score FLOAT,
    PRIMARY KEY (time_generated, cow_id, sensor_id),
    FOREIGN KEY (cow_id) REFERENCES cow(cow_id) ON DELETE CASCADE,
    FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id)
);