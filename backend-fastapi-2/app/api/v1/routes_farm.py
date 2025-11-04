# app/api/v1/routes_farm.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import get_postgres_conn, get_mongo_db
from app.services import farm_service
from app.schemas import (
    CowCreateRequest,
    CowUpdateRequest,
    CowResponse,
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorResponse,
    MessageResponse,
    SensorDataResponse
)
from typing import Optional, List

router = APIRouter(prefix="/farm", tags=["Farm Management"])

@router.post("/cow", response_model=CowResponse)
async def create_cow(
    request: CowCreateRequest,
    conn=Depends(get_postgres_conn)
):
    """
    Create a new cow for a farmer.

    - **farmer_id**: UUID of the farmer who owns the cow
    - **name**: Cow's name
    - **age**: Cow's age in years
    """
    try:
        cow = await farm_service.create_cow(
            conn,
            request.farmer_id,
            request.name,
            request.age
        )
        return CowResponse(**cow)
    except Exception as e:
        error_msg = str(e)
        if "foreign key constraint" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid farmer_id. Farmer not found: {request.farmer_id}"
            )
        elif "violates unique constraint" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Cow with this name already exists for this farmer"
            )
        else:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/cow", response_model=List[CowResponse])
async def get_cows(
    farmer_id: str = Query(..., description="UUID of the farmer"),
    conn=Depends(get_postgres_conn)
):
    """
    Get all cows for a specific farmer.

    - **farmer_id**: UUID of the farmer
    """
    cows = await farm_service.get_cows(conn, farmer_id)
    return [CowResponse(**cow) for cow in cows]

@router.put("/cow/{cow_id}", response_model=CowResponse)
async def update_cow(
    cow_id: str,
    request: CowUpdateRequest,
    conn=Depends(get_postgres_conn)
):
    """
    Update cow information.

    - **cow_id**: UUID of the cow to update
    - **name**: New name (optional)
    - **age**: New age (optional)
    """
    cow = await farm_service.update_cow(
        conn,
        cow_id,
        request.name,
        request.age
    )
    return CowResponse(**cow)

@router.delete("/cow/{cow_id}", response_model=MessageResponse)
async def delete_cow(
    cow_id: str,
    conn=Depends(get_postgres_conn)
):
    """
    Delete a cow.

    - **cow_id**: UUID of the cow to delete
    """
    result = await farm_service.delete_cow(conn, cow_id)
    return MessageResponse(**result)

@router.post("/sensor", response_model=SensorResponse)
async def create_sensor(
    request: SensorCreateRequest,
    conn=Depends(get_postgres_conn)
):
    """
    Create a new sensor.

    - **status**: 1 for active, 0 for inactive (default: 1)
    """
    try:
        sensor = await farm_service.create_sensor(conn, request.status)
        return SensorResponse(**sensor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating sensor: {str(e)}")

@router.get("/sensor", response_model=List[SensorResponse])
async def get_sensors(conn=Depends(get_postgres_conn)):
    """
    Get all sensors.
    """
    sensors = await farm_service.get_sensors(conn)
    return [SensorResponse(**sensor) for sensor in sensors]

@router.put("/sensor/{sensor_id}", response_model=SensorResponse)
async def update_sensor(
    sensor_id: str,
    request: SensorUpdateRequest,
    conn=Depends(get_postgres_conn)
):
    """
    Update sensor status.

    - **sensor_id**: UUID of the sensor to update
    - **status**: New status (1=active, 0=inactive)
    """
    sensor = await farm_service.update_sensor(conn, sensor_id, request.status)
    return SensorResponse(**sensor)

@router.delete("/sensor/{sensor_id}", response_model=MessageResponse)
async def delete_sensor(
    sensor_id: str,
    conn=Depends(get_postgres_conn)
):
    """
    Delete a sensor.

    - **sensor_id**: UUID of the sensor to delete
    """
    result = await farm_service.delete_sensor(conn, sensor_id)
    return MessageResponse(**result)

@router.get("/sensor-data", response_model=SensorDataResponse)
async def get_sensor_data(
    cow_id: Optional[int] = Query(None, description="Filter by cow ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return (max 1000)")
):
    """
    Fetch sensor data from MongoDB.

    - **cow_id**: Filter by specific cow ID (optional)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)

    Returns sensor readings sorted by timestamp (most recent first).
    """
    db = get_mongo_db()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")

    collection = db["sensor_data"]

    # Build query filter
    query = {}
    if cow_id is not None:
        query["cow_id"] = cow_id

    # Fetch data sorted by timestamp (most recent first)
    cursor = collection.find(query).sort("timestamp", -1).limit(limit)
    sensor_data = []

    async for document in cursor:
        # Convert MongoDB ObjectId to string for JSON serialization
        document["_id"] = str(document["_id"])
        sensor_data.append(document)

    return SensorDataResponse(data=sensor_data, count=len(sensor_data))