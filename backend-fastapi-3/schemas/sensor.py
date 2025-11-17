# schemas/sensor.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class SensorDataPoint(BaseModel):
    """
    Mewakili satu baris data dari 'output_sensor'.
    """
    timestamp: datetime
    device_id: str
    rfid_id: str
    weight: float | None = None
    temperature_c: float | None = None
    ip: str | None = None

    class Config:
        from_attributes = True