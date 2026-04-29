from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.user_request import UserRequest


async def test_request_log_created_after_cbr_call(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    mock_cbr_loaders,
    mock_minio,
) -> None:
    # Count records before the call
    count_before = (await db_session.execute(
        select(func.count()).where(UserRequest.source == "cbr", UserRequest.endpoint == "key_rate")
    )).scalar()

    resp = await client.get(
        "/cbr/key_rate",
        params={"first_date": "2024-01-01", "last_date": "2024-06-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    count_after = (await db_session.execute(
        select(func.count()).where(UserRequest.source == "cbr", UserRequest.endpoint == "key_rate")
    )).scalar()
    assert count_after == count_before + 1

    # Verify the most recent record has correct values
    result = await db_session.execute(
        select(UserRequest)
        .where(UserRequest.source == "cbr", UserRequest.endpoint == "key_rate")
        .order_by(UserRequest.requested_at.desc())
        .limit(1)
    )
    record = result.scalar_one()
    assert record.rows_downloaded == 42
    assert record.parameters == {"first_date": "2024-01-01", "last_date": "2024-06-01"}


async def test_request_log_created_after_moex_call(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    mock_moex_loaders,
    mock_minio,
) -> None:
    count_before = (await db_session.execute(
        select(func.count()).where(UserRequest.source == "moex", UserRequest.endpoint == "shares")
    )).scalar()

    resp = await client.get(
        "/moex/shares",
        params={"ticker": "SBER", "period": "ONE_DAY", "first_date": "2025-01-01", "last_date": "2025-03-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    count_after = (await db_session.execute(
        select(func.count()).where(UserRequest.source == "moex", UserRequest.endpoint == "shares")
    )).scalar()
    assert count_after == count_before + 1

    result = await db_session.execute(
        select(UserRequest)
        .where(UserRequest.source == "moex", UserRequest.endpoint == "shares")
        .order_by(UserRequest.requested_at.desc())
        .limit(1)
    )
    record = result.scalar_one()
    assert record.rows_downloaded == 42


async def test_no_log_on_loader_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    mock_minio,
    monkeypatch,
) -> None:
    import loader.cbr.cbr as cbr_loader
    monkeypatch.setattr(cbr_loader, "reserves", lambda **kw: 0)

    count_before = (await db_session.execute(
        select(func.count()).where(UserRequest.source == "cbr", UserRequest.endpoint == "reserves")
    )).scalar()

    resp = await client.get(
        "/cbr/reserves",
        params={"first_date": "2024-01-01", "last_date": "2024-06-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 502

    count_after = (await db_session.execute(
        select(func.count()).where(UserRequest.source == "cbr", UserRequest.endpoint == "reserves")
    )).scalar()
    assert count_after == count_before
