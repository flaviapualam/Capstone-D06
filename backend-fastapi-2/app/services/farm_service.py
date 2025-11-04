# app/services/farm_services.py
from fastapi import HTTPException

async def create_cow(conn, farmer_id: str, name: str, age: int):
    query = """
        INSERT INTO farm.cow (farmer_id, name, age)
        VALUES ($1, $2, $3)
        RETURNING cow_id, farmer_id, name, age
    """
    record = await conn.fetchrow(query, farmer_id, name, age)
    return dict(record)

async def get_cows(conn, farmer_id: str):
    query = "SELECT cow_id, farmer_id, name, age FROM farm.cow WHERE farmer_id = $1"
    rows = await conn.fetch(query, farmer_id)
    return [dict(r) for r in rows]

async def get_cow_by_id(conn, cow_id: str):
    query = "SELECT cow_id, farmer_id, name, age FROM farm.cow WHERE cow_id = $1"
    record = await conn.fetchrow(query, cow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Cow not found")
    return dict(record)

async def update_cow(conn, cow_id: str, name: str | None = None, age: int | None = None):
    query = "UPDATE farm.cow SET name = COALESCE($2, name), age = COALESCE($3, age) WHERE cow_id = $1 RETURNING cow_id, farmer_id, name, age"
    record = await conn.fetchrow(query, cow_id, name, age)
    if not record:
        raise HTTPException(status_code=404, detail="Cow not found")
    return dict(record)

async def delete_cow(conn, cow_id: str):
    query = "DELETE FROM farm.cow WHERE cow_id = $1 RETURNING cow_id"
    record = await conn.fetchrow(query, cow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Cow not found")
    return {"message": "Cow deleted successfully"}

async def create_sensor(conn, status: int):
    try:
        query = "INSERT INTO farm.sensor (status) VALUES ($1) RETURNING sensor_id, status"
        record = await conn.fetchrow(query, status)
        if not record:
            raise HTTPException(status_code=400, detail="Failed to create sensor")
        return dict(record)
    except Exception as e:
        print(f"DEBUG create_sensor error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating sensor: {str(e)}")

async def get_sensors(conn):
    query = "SELECT * FROM farm.sensor"
    rows = await conn.fetch(query)
    return [dict(r) for r in rows]

async def update_sensor(conn, sensor_id: str, status: int):
    query = "UPDATE farm.sensor SET status = $2 WHERE sensor_id = $1 RETURNING *"
    record = await conn.fetchrow(query, sensor_id, status)
    if not record:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return dict(record)

async def delete_sensor(conn, sensor_id: str):
    query = "DELETE FROM farm.sensor WHERE sensor_id = $1 RETURNING sensor_id"
    record = await conn.fetchrow(query, sensor_id)
    if not record:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return {"message": "Sensor deleted successfully"}