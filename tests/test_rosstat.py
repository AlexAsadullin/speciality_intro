import pytest
from httpx import AsyncClient

ROSSTAT_ENDPOINTS = ["/rosstat/cpi", "/rosstat/ipp"]


@pytest.mark.parametrize("endpoint", ROSSTAT_ENDPOINTS)
async def test_rosstat_success(
    client: AsyncClient,
    auth_headers: dict,
    mock_rosstat_loaders,
    mock_minio,
    endpoint: str,
) -> None:
    resp = await client.get(endpoint, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows_downloaded"] == 42


@pytest.mark.parametrize("endpoint", ROSSTAT_ENDPOINTS)
async def test_rosstat_unauthenticated(client: AsyncClient, endpoint: str) -> None:
    resp = await client.get(endpoint)
    assert resp.status_code in (401, 403)


@pytest.mark.parametrize("endpoint", ROSSTAT_ENDPOINTS)
async def test_rosstat_loader_failure_502(
    client: AsyncClient,
    auth_headers: dict,
    mock_minio,
    monkeypatch,
    endpoint: str,
) -> None:
    loader_name = endpoint.removeprefix("/rosstat/")
    import loader.rosstat.parsers as rosstat_loader
    monkeypatch.setattr(rosstat_loader, loader_name, lambda: 0)

    resp = await client.get(endpoint, headers=auth_headers)
    assert resp.status_code == 502
