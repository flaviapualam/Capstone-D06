# schemas/rfid.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class RfidAssignRequest(BaseModel):
    """
    Skema Input untuk body POST /api/rfid/assign
    """
    rfid_id: str
    cow_id: UUID

class RfidOwnershipResponse(BaseModel):
    """
    Skema Output yang mewakili satu baris di rfid_ownership
    """
    rfid_id: str
    time_start: datetime
    cow_id: UUID
    time_end: datetime | None = None

    class Config:
        from_attributes = True