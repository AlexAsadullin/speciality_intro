from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import loader.rosstat.parsers as rosstat_loader
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import ErrorResponse, LoaderResponse
from app.services.loader_runner import run_loader

router = APIRouter(
    prefix="/rosstat",
    tags=["Rosstat"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        502: {"model": ErrorResponse, "description": "Upstream returned no data"},
        503: {"model": ErrorResponse, "description": "MinIO unavailable"},
    },
)


@router.get(
    "/cpi",
    response_model=LoaderResponse,
    summary="Download Rosstat weekly CPI (fedstat id=31074)",
    responses={200: {"description": "CPI data downloaded and stored"}},
)
async def get_cpi(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(rosstat_loader.cpi, {}, "rosstat", "cpi", current_user.id, db)
    return LoaderResponse(**result)


@router.get(
    "/ipp",
    response_model=LoaderResponse,
    summary="Download Rosstat industrial producer price index (fedstat id=40557)",
    responses={200: {"description": "IPP data downloaded and stored"}},
)
async def get_ipp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoaderResponse:
    result = await run_loader(rosstat_loader.ipp, {}, "rosstat", "ipp", current_user.id, db)
    return LoaderResponse(**result)
