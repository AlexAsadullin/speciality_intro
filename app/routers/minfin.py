from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import loader.minfin.parsers as minfin_loader
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import ErrorResponse, LoaderResponse
from app.services.loader_runner import run_loader

router = APIRouter(
    prefix="/minfin",
    tags=["Minfin"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        502: {"model": ErrorResponse, "description": "Upstream returned no data"},
        503: {"model": ErrorResponse, "description": "MinIO unavailable"},
    },
)


@router.get(
    "/budget",
    response_model=LoaderResponse,
    summary="Download Minfin federal budget execution data (OpenData)",
)
async def get_budget(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(minfin_loader.budget, {}, "minfin", "budget", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/fnb",
    response_model=LoaderResponse,
    summary="Download National Wealth Fund (FNB) balance data (OpenData)",
)
async def get_fnb(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(minfin_loader.fnb, {}, "minfin", "fnb", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/ofz_auctions",
    response_model=LoaderResponse,
    summary="Scrape OFZ auction document cards from minfin.gov.ru",
)
async def get_ofz_auctions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(minfin_loader.ofz_auctions, {}, "minfin", "ofz_auctions", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/state_support",
    response_model=LoaderResponse,
    summary="Scrape state budget support document cards from minfin.gov.ru",
)
async def get_state_support(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(minfin_loader.state_support, {}, "minfin", "state_support", current_user.id, db)
    return LoaderResponse(**result)
