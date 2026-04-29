import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, username: str | None = None, email: str | None = None) -> dict:
    uid = str(uuid.uuid4())[:8]
    payload = {
        "username": username or f"user_{uid}",
        "email": email or f"user_{uid}@test.com",
        "password": "password123",
    }
    resp = await client.post("/auth/register", json=payload)
    return {"resp": resp, "payload": payload}


async def test_register_success(client: AsyncClient) -> None:
    data = await _register(client)
    assert data["resp"].status_code == 201
    body = data["resp"].json()
    assert body["username"] == data["payload"]["username"]
    assert "id" in body


async def test_register_duplicate_username(client: AsyncClient) -> None:
    data = await _register(client)
    assert data["resp"].status_code == 201
    dup = await client.post("/auth/register", json={
        "username": data["payload"]["username"],
        "email": "other@test.com",
        "password": "password123",
    })
    assert dup.status_code == 409


async def test_register_duplicate_email(client: AsyncClient) -> None:
    data = await _register(client)
    assert data["resp"].status_code == 201
    dup = await client.post("/auth/register", json={
        "username": "totally_different",
        "email": data["payload"]["email"],
        "password": "password123",
    })
    assert dup.status_code == 409


async def test_register_short_password(client: AsyncClient) -> None:
    uid = str(uuid.uuid4())[:8]
    resp = await client.post("/auth/register", json={
        "username": f"user_{uid}",
        "email": f"user_{uid}@test.com",
        "password": "short",
    })
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient) -> None:
    data = await _register(client)
    resp = await client.post("/auth/login", json={
        "username": data["payload"]["username"],
        "password": data["payload"]["password"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    data = await _register(client)
    resp = await client.post("/auth/login", json={
        "username": data["payload"]["username"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post("/auth/login", json={
        "username": "nonexistent_user_xyz",
        "password": "password123",
    })
    assert resp.status_code == 401


async def test_refresh_success(client: AsyncClient) -> None:
    data = await _register(client)
    login_resp = await client.post("/auth/login", json={
        "username": data["payload"]["username"],
        "password": data["payload"]["password"],
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/auth/refresh", json={"refresh_token": "not.a.valid.token"})
    assert resp.status_code == 401


async def test_logout_invalidates_refresh_token(client: AsyncClient, auth_headers: dict) -> None:
    # Get a fresh login to have a refresh token
    uid = str(uuid.uuid4())[:8]
    await client.post("/auth/register", json={
        "username": f"logoutuser_{uid}",
        "email": f"logout_{uid}@test.com",
        "password": "password123",
    })
    login_resp = await client.post("/auth/login", json={
        "username": f"logoutuser_{uid}",
        "password": "password123",
    })
    tokens = login_resp.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    logout_resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert logout_resp.status_code == 204

    # Refresh token should no longer work
    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert refresh_resp.status_code == 401


async def test_protected_endpoint_without_token(client: AsyncClient) -> None:
    resp = await client.get("/cbr/key_rate")
    assert resp.status_code in (401, 403)
