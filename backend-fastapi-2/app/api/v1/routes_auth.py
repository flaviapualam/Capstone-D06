# app/api/v1/routes_auth.py
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from app.core.database import get_postgres_conn
from app.services.auth_service import register_farmer, authenticate_farmer

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(request: Request, conn=Depends(get_postgres_conn)):
    body = await request.json()
    name = body.get("name")
    email = body.get("email")
    password = body.get("password")

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="name, email, and password required")

    new_farmer = await register_farmer(conn, name, email, password)
    return {"message": "Farmer registered successfully", "data": new_farmer}


@router.post("/login")
async def login(request: Request, response: Response, conn=Depends(get_postgres_conn)):
    body = await request.json()
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")

    farmer = await authenticate_farmer(conn, email, password)
    if not farmer:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    response.set_cookie(
        key="farmer_id",
        value=str(farmer["farmer_id"]),
        httponly=True,
        samesite="lax"
    )

    return {"message": "Login successful"}