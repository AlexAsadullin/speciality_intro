from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

import loader.moex.algopack as moex_loader
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import ErrorResponse, LoaderResponse
from app.services.loader_runner import run_loader
from config import MOEX_DEFAULT_FIRST_DATE, MOEX_DEFAULT_LAST_DATE


class CandlePeriodParam(str, Enum):
    ONE_MINUTE = "ONE_MINUTE"
    TEN_MINUTES = "TEN_MINUTES"
    ONE_HOUR = "ONE_HOUR"
    ONE_DAY = "ONE_DAY"
    ONE_WEEK = "ONE_WEEK"
    ONE_MONTH = "ONE_MONTH"


router = APIRouter(
    prefix="/moex",
    tags=["MOEX"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        502: {"model": ErrorResponse, "description": "Upstream returned no data or 403 (AlgoPack token required)"},
        503: {"model": ErrorResponse, "description": "MinIO unavailable"},
    },
)


def _date_query(
    first_date: str = Query(default=MOEX_DEFAULT_FIRST_DATE, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    last_date: str = Query(default=MOEX_DEFAULT_LAST_DATE, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    if first_date > last_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="first_date must be <= last_date")
    return {"first_date": first_date, "last_date": last_date}


@router.get(
    "/shares",
    response_model=LoaderResponse,
    summary="Download MOEX share candles for a ticker",
    description="Candle data for any CandlePeriod. No AlgoPack subscription needed.",
)
async def get_shares(
    ticker: str = Query(..., description="MOEX ticker, e.g. SBER"),
    period: CandlePeriodParam = Query(default=CandlePeriodParam.ONE_DAY, description="Candle period"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    from moexalgo import CandlePeriod
    kwargs = {**dates, "ticker": ticker, "period": CandlePeriod[period.value]}
    result = await run_loader(moex_loader.shares, kwargs, "moex", "shares", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/orderbook",
    response_model=LoaderResponse,
    summary="Download MOEX orderbook stats (obstats) — requires AlgoPack subscription",
)
async def get_orderbook(
    ticker: str = Query(..., description="MOEX ticker, e.g. SBER"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    kwargs = {**dates, "ticker": ticker}
    result = await run_loader(moex_loader.orderbook, kwargs, "moex", "orderbook", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/tradestats",
    response_model=LoaderResponse,
    summary="Download MOEX trade statistics — requires AlgoPack subscription",
)
async def get_tradestats(
    ticker: str = Query(..., description="MOEX ticker, e.g. SBER"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    kwargs = {**dates, "ticker": ticker}
    result = await run_loader(moex_loader.tradestats, kwargs, "moex", "tradestats", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/orderstats",
    response_model=LoaderResponse,
    summary="Download MOEX order statistics — requires AlgoPack subscription",
)
async def get_orderstats(
    ticker: str = Query(..., description="MOEX ticker, e.g. SBER"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    kwargs = {**dates, "ticker": ticker}
    result = await run_loader(moex_loader.orderstats, kwargs, "moex", "orderstats", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/indices",
    response_model=LoaderResponse,
    summary="Download MOEX index daily candles",
)
async def get_indices(
    ticker: str = Query(..., description="MOEX index ticker, e.g. IMOEX"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    kwargs = {**dates, "ticker": ticker}
    result = await run_loader(moex_loader.indices, kwargs, "moex", "indices", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/ofz_curve",
    response_model=LoaderResponse,
    summary="Download OFZ yield curve index (RGBI/RGBITR) daily candles",
)
async def get_ofz_curve(
    ticker: str = Query(default="RGBI", description="OFZ index ticker, e.g. RGBI"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    kwargs = {**dates, "ticker": ticker}
    result = await run_loader(moex_loader.ofz_curve, kwargs, "moex", "ofz_curve", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/derivatives",
    response_model=LoaderResponse,
    summary="Download MOEX futures daily candles",
)
async def get_derivatives(
    ticker: str = Query(..., description="Futures ticker, e.g. SiH6"),
    dates: dict = Depends(_date_query),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    kwargs = {**dates, "ticker": ticker}
    result = await run_loader(moex_loader.derivatives, kwargs, "moex", "derivatives", current_user.id, db)
    return LoaderResponse(**result)
