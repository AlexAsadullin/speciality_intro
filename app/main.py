import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import LoaderError, MinIOError
from app.settings import get_settings

settings = get_settings()
# Apply DATA_ROOT before any loader import happens
os.environ.setdefault("DATA_ROOT", settings.data_root)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.minio_client import ensure_bucket
    await ensure_bucket(settings.minio_bucket)
    yield


app = FastAPI(
    title="Trading Data API",
    description="REST API для сбора финансовых данных: CBR, MOEX, Rosstat, Minfin",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(LoaderError)
async def loader_error_handler(request: Request, exc: LoaderError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc), "type": "loader_error"},
    )


@app.exception_handler(MinIOError)
async def minio_error_handler(request: Request, exc: MinIOError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc), "type": "storage_error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "type": "validation_error"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": "internal_error"},
    )


# Routers
from app.auth.router import router as auth_router
from app.routers.cbr import router as cbr_router
from app.routers.minfin import router as minfin_router
from app.routers.moex import router as moex_router
from app.routers.rosstat import router as rosstat_router

app.include_router(auth_router)
app.include_router(cbr_router)
app.include_router(moex_router)
app.include_router(rosstat_router)
app.include_router(minfin_router)
