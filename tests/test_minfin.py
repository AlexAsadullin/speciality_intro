import pytest
from httpx import AsyncClient

MINFIN_ENDPOINTS = ["/minfin/budget", "/minfin/fnb", "/minfin/ofz_auctions", "/minfin/state_support"]


@pytest.mark.parametrize("endpoint", MINFIN_ENDPOINTS)
async def test_minfin_success(
    client: AsyncClient,
    auth_headers: dict,
    mock_minfin_loaders,
    mock_minio,
    endpoint: str,
) -> None:
    resp = await client.get(endpoint, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows_downloaded"] == 42


@pytest.mark.parametrize("endpoint", MINFIN_ENDPOINTS)
async def test_minfin_unauthenticated(client: AsyncClient, endpoint: str) -> None:
    resp = await client.get(endpoint)
    assert resp.status_code in (401, 403)


@pytest.mark.parametrize("endpoint", MINFIN_ENDPOINTS)
async def test_minfin_loader_failure_502(
    client: AsyncClient,
    auth_headers: dict,
    mock_minio,
    monkeypatch,
    endpoint: str,
) -> None:
    loader_name = endpoint.removeprefix("/minfin/")
    import loader.minfin.parsers as minfin_loader
    monkeypatch.setattr(minfin_loader, loader_name, lambda: 0)

    resp = await client.get(endpoint, headers=auth_headers)
    assert resp.status_code == 502
