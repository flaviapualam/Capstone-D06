from fastapi import FastAPI
from app.core.config import settings
from app.api import api_router
from app.core.database import connect_to_mongo, close_mongo_connection, connect_to_postgres, close_postgres_connection

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION
    )
    app.include_router(api_router)

    # Startup & Shutdown events
    @app.on_event("startup")
    async def startup_db_client():
        await connect_to_mongo()
        await connect_to_postgres()

    @app.on_event("shutdown")
    async def shutdown_db_client():
        await close_mongo_connection()
        await close_postgres_connection()
    return app

app = create_app()
