# app/api/v1/routes_auth.py
from fastapi import APIRouter, Depends, Response, HTTPException
from app.core.database import get_postgres_conn
from app.services.auth_service import register_farmer, authenticate_farmer
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    LoginResponse,
    FarmerResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    conn=Depends(get_postgres_conn)
):
    """
    Register a new farmer account.

    - **name**: Farmer's full name
    - **email**: Valid email address (must be unique)
    - **password**: Password with minimum 6 characters
    """
    new_farmer = await register_farmer(conn, request.name, request.email, request.password)
    return RegisterResponse(
        message="Farmer registered successfully",
        data=FarmerResponse(**new_farmer)
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    conn=Depends(get_postgres_conn)
):
    """
    Login with email and password.

    - **email**: Registered email address
    - **password**: Account password

    Returns farmer information and sets an HTTP-only cookie for session management.
    """
    farmer = await authenticate_farmer(conn, request.email, request.password)
    if not farmer:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    response.set_cookie(
        key="farmer_id",
        value=str(farmer["farmer_id"]),
        httponly=True,
        samesite="lax"
    )

    return LoginResponse(
        message="Login successful",
        farmer_id=farmer["farmer_id"],
        name=farmer["name"],
        email=farmer["email"]
    )