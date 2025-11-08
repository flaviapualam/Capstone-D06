# core/security.py
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Cookie
from core.config import settings
from db.postgresql import get_db_connection
from services import authentication
from schemas.farmer import FarmerResponse
from schemas.token import TokenData
import asyncpg

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def get_token_from_cookie(access_token: str = Cookie(None)) -> str | None:
    """
    Dependency untuk mengekstrak token dari cookie.
    'access_token' harus cocok dengan 'key' yang kita set di set_cookie.
    """
    if not access_token:
        return None
    
    # Cookie kita berisi "Bearer <token>", kita hanya perlu <token>-nya
    parts = access_token.split()
    if len(parts) == 2 and parts[0] == "Bearer":
        return parts[1]
    return None # Format cookie salah


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

async def get_current_farmer(
    # 'token' sekarang diambil dari dependency 'get_token_from_cookie'
    token: str = Depends(get_token_from_cookie),
    db: asyncpg.Connection = Depends(get_db_connection)
) -> FarmerResponse:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    if token is None:
        raise credentials_exception
    
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    farmer_record = await authentication.get_farmer_by_email(db, email=token_data.email)
    if farmer_record is None:
        raise credentials_exception
    return FarmerResponse.model_validate(dict(farmer_record))