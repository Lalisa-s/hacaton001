from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.db.demo import initialize_demo_database
from app.db.session import create_db_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    db_engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        try:
            if settings.demo_mode:
                initialize_demo_database(db_engine)
            yield
        finally:
            db_engine.dispose()

    application = FastAPI(
        title=settings.app_name, version="0.2.0", lifespan=lifespan,
        description="Учебное демо на вымышленных данных. DEMO_MODE и X-Demo-User-Id не являются авторизацией.",
    )
    application.state.settings = settings
    application.state.db_engine = db_engine
    application.state.session_factory = sessionmaker(
        bind=db_engine, autoflush=False, expire_on_commit=False,
    )
    install_error_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Demo-User-Id"],
    )
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
