import pytest
from httpx import AsyncClient

TICKER_ENDPOINTS = [
    "/moex/orderbook",
    "/moex/tradestats",
    "/moex/orderstats",
    "/moex/indices",
    "/moex/ofz_curve",
    "/moex/derivatives",
]

# ofz_curve has a default ticker (RGBI), so "missing ticker" doesn't apply
TICKER_REQUIRED_ENDPOINTS = [ep for ep in TICKER_ENDPOINTS if ep != "/moex/ofz_curve"]

DATE_PARAMS = {"first_date": "2025-01-01", "last_date": "2025-03-01"}


async def test_shares_success(
    client: AsyncClient,
    auth_headers: dict,
    mock_moex_loaders,
    mock_minio,
) -> None:
    resp = await client.get(
        "/moex/shares",
        params={"ticker": "SBER", "period": "ONE_DAY", **DATE_PARAMS},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows_downloaded"] == 42


async def test_shares_invalid_period(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get(
        "/moex/shares",
        params={"ticker": "SBER", "period": "INVALID_PERIOD", **DATE_PARAMS},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_shares_missing_ticker(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get("/moex/shares", params={"period": "ONE_DAY", **DATE_PARAMS}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", TICKER_ENDPOINTS)
async def test_ticker_endpoint_success(
    client: AsyncClient,
    auth_headers: dict,
    mock_moex_loaders,
    mock_minio,
    endpoint: str,
) -> None:
    resp = await client.get(endpoint, params={"ticker": "SBER", **DATE_PARAMS}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows_downloaded"] == 42


@pytest.mark.parametrize("endpoint", TICKER_REQUIRED_ENDPOINTS)
async def test_ticker_endpoint_missing_ticker(client: AsyncClient, auth_headers: dict, endpoint: str) -> None:
    resp = await client.get(endpoint, params=DATE_PARAMS, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", TICKER_ENDPOINTS)
async def test_ticker_endpoint_inverted_dates(client: AsyncClient, auth_headers: dict, endpoint: str) -> None:
    resp = await client.get(endpoint, params={"ticker": "SBER", "first_date": "2025-06-01", "last_date": "2025-01-01"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", TICKER_ENDPOINTS)
async def test_ticker_endpoint_unauthenticated(client: AsyncClient, endpoint: str) -> None:
    resp = await client.get(endpoint, params={"ticker": "SBER", **DATE_PARAMS})
    assert resp.status_code in (401, 403)
