# app/services/auth_service.py
from app.core.security import hash_password, verify_password
from fastapi import HTTPException, status
import uuid

async def register_farmer(conn, name: str, email: str, password: str):
    query_check = "SELECT * FROM auth.farmer WHERE email = $1"
    existing = await conn.fetchrow(query_check, email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(password)
    farmer_id = str(uuid.uuid4())

    query_insert = """
        INSERT INTO auth.farmer (farmer_id, name, email, password_hash)
        VALUES ($1, $2, $3, $4)
        RETURNING farmer_id, name, email
    """
    record = await conn.fetchrow(query_insert, farmer_id, name, email, hashed_pw)
    return dict(record)

async def authenticate_farmer(conn, email: str, password: str):
    query = "SELECT farmer_id, name, email, password_hash FROM auth.farmer WHERE email = $1"
    farmer = await conn.fetchrow(query, email)

    if not farmer:
        return None

    if not verify_password(password, farmer["password_hash"]):
        return None

    return dict(farmer)