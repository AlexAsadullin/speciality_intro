import pytest
from httpx import AsyncClient

CBR_ENDPOINTS = [
    "/cbr/key_rate",
    "/cbr/refinancing_rate",
    "/cbr/ruonia",
    "/cbr/currency_rates",
    "/cbr/reserves",
    "/cbr/metals_prices",
    "/cbr/ibor",
    "/cbr/roisfix",
]


@pytest.mark.parametrize("endpoint", CBR_ENDPOINTS)
async def test_cbr_success(
    client: AsyncClient,
    auth_headers: dict,
    mock_cbr_loaders,
    mock_minio,
    endpoint: str,
) -> None:
    resp = await client.get(endpoint, params={"first_date": "2024-01-01", "last_date": "2024-06-01"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["rows_downloaded"] == 42
    assert isinstance(body["files"], list)


@pytest.mark.parametrize("endpoint", CBR_ENDPOINTS)
async def test_cbr_unauthenticated(client: AsyncClient, endpoint: str) -> None:
    resp = await client.get(endpoint, params={"first_date": "2024-01-01", "last_date": "2024-06-01"})
    assert resp.status_code in (401, 403)


@pytest.mark.parametrize("endpoint", CBR_ENDPOINTS)
async def test_cbr_invalid_date_format(client: AsyncClient, auth_headers: dict, endpoint: str) -> None:
    resp = await client.get(endpoint, params={"first_date": "01-01-2024", "last_date": "2024-06-01"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", CBR_ENDPOINTS)
async def test_cbr_date_range_inverted(client: AsyncClient, auth_headers: dict, endpoint: str) -> None:
    resp = await client.get(endpoint, params={"first_date": "2024-06-01", "last_date": "2024-01-01"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", CBR_ENDPOINTS)
async def test_cbr_loader_failure_returns_502(
    client: AsyncClient,
    auth_headers: dict,
    mock_minio,
    monkeypatch,
    endpoint: str,
) -> None:
    # Patch the specific loader to return 0
    loader_name = endpoint.removeprefix("/cbr/")
    import loader.cbr.cbr as cbr_loader
    monkeypatch.setattr(cbr_loader, loader_name, lambda **kw: 0)

    resp = await client.get(endpoint, params={"first_date": "2024-01-01", "last_date": "2024-06-01"}, headers=auth_headers)
    assert resp.status_code == 502
