from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

import loader.cbr.cbr as cbr_loader
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import ErrorResponse, LoaderResponse
from app.services.loader_runner import run_loader
from config import CBR_DEFAULT_FIRST_DATE, CBR_DEFAULT_LAST_DATE

router = APIRouter(
    prefix="/cbr",
    tags=["CBR"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        502: {"model": ErrorResponse, "description": "Upstream returned no data"},
        503: {"model": ErrorResponse, "description": "MinIO unavailable"},
    },
)

_DATE_PARAMS = {
    "first_date": Query(default=CBR_DEFAULT_FIRST_DATE, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date YYYY-MM-DD"),
    "last_date": Query(default=CBR_DEFAULT_LAST_DATE, pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date YYYY-MM-DD"),
}


def _date_query(first_date: str = Query(default=CBR_DEFAULT_FIRST_DATE, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                last_date: str = Query(default=CBR_DEFAULT_LAST_DATE, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    if first_date > last_date:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="first_date must be <= last_date")
    return {"first_date": first_date, "last_date": last_date}


@router.get("/key_rate", response_model=LoaderResponse, summary="Download CBR key rate data")
async def get_key_rate(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.key_rate, dates, "cbr", "key_rate", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/refinancing_rate", response_model=LoaderResponse, summary="Download CBR refinancing rate data")
async def get_refinancing_rate(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.refinancing_rate, dates, "cbr", "refinancing_rate", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/ruonia", response_model=LoaderResponse, summary="Download RUONIA index")
async def get_ruonia(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.ruonia, dates, "cbr", "ruonia", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/currency_rates", response_model=LoaderResponse, summary="Download CBR currency exchange rates (USD/EUR/CNY)")
async def get_currency_rates(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.currency_rates, dates, "cbr", "currency_rates", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/reserves", response_model=LoaderResponse, summary="Download CBR international reserves")
async def get_reserves(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.reserves, dates, "cbr", "reserves", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/metals_prices", response_model=LoaderResponse, summary="Download CBR accounting prices for precious metals")
async def get_metals_prices(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.metals_prices, dates, "cbr", "metals_prices", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/ibor", response_model=LoaderResponse, summary="Download IBOR rates from CBR")
async def get_ibor(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.ibor, dates, "cbr", "ibor", current_user.id, db)
    return LoaderResponse(**result)


@router.get("/roisfix", response_model=LoaderResponse, summary="Download ROISFIX rates from CBR")
async def get_roisfix(
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(cbr_loader.roisfix, dates, "cbr", "roisfix", current_user.id, db)
    return LoaderResponse(**result)
