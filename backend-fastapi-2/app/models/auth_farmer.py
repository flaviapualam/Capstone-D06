# app/models/auth_farmer.py
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class Farmer(Base):
    __tablename__ = "farmer"
    __table_args__ = {"schema": "auth"}

    farmer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable= False)
    email = Column(String(50), unique=True, nullable=True, index=True)
    password_hash = Column(Text, nullable=False)