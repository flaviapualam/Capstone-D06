# app/api/v1/routes_farm.py
from fastapi import APIRouter, Depends, Request, HTTPException
from app.core.database import get_postgres_conn
from app.services import farm_service

router = APIRouter(prefix="/farm", tags=["Farm Management"])

@router.post("/cow")
async def create_cow(request: Request, conn=Depends(get_postgres_conn)):
    data = await request.json()
    farmer_id = data.get("farmer_id")
    name = data.get("name")
    age = data.get("age")
    status = data.get("status", 1)
    if not all([farmer_id, name, age]):
        raise HTTPException(status_code=400, detail="farmer_id, name, and age required")
    cow = await farm_service.create_cow(conn, farmer_id, name, age, status)
    return cow

@router.get("/cow")
async def get_cows(farmer_id: str, conn=Depends(get_postgres_conn)):
    return await farm_service.get_cows(conn, farmer_id)

@router.put("/cow/{cow_id}")
async def update_cow(cow_id: str, request: Request, conn=Depends(get_postgres_conn)):
    data = await request.json()
    cow = await farm_service.update_cow(conn, cow_id, data.get("name"), data.get("age"), data.get("status"))
    return cow

@router.delete("/cow/{cow_id}")
async def delete_cow(cow_id: str, conn=Depends(get_postgres_conn)):
    return await farm_service.delete_cow(conn, cow_id)

@router.post("/sensor")
async def create_sensor(request: Request, conn=Depends(get_postgres_conn)):
    data = await request.json()
    status = data.get("status", 1)
    return await farm_service.create_sensor(conn, status)

@router.get("/sensor")
async def get_sensors(conn=Depends(get_postgres_conn)):
    return await farm_service.get_sensors(conn)

@router.put("/sensor/{sensor_id}")
async def update_sensor(sensor_id: str, request: Request, conn=Depends(get_postgres_conn)):
    data = await request.json()
    status = data.get("status")
    return await farm_service.update_sensor(conn, sensor_id, status)

@router.delete("/sensor/{sensor_id}")
async def delete_sensor(sensor_id: str, conn=Depends(get_postgres_conn)):
    return await farm_service.delete_sensor(conn, sensor_id)