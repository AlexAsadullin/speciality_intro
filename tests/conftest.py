import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use SQLite in-memory for tests (no external Postgres needed)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests-only")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "testtest")
os.environ.setdefault("DATA_ROOT", "/tmp/test_trading_data")

# Must be set before app imports
from app.settings import get_settings  # noqa: E402

get_settings.cache_clear()


from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import user, user_request  # noqa: F401, E402 — register models


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_minio(monkeypatch):
    uploaded: list[str] = []

    async def _upload(local_path: str, object_key: str) -> None:
        uploaded.append(object_key)

    async def _ensure(bucket: str) -> None:
        pass

    monkeypatch.setattr("app.services.minio_client.upload_file", _upload)
    monkeypatch.setattr("app.services.loader_runner.upload_file", _upload)
    monkeypatch.setattr("app.services.minio_client.ensure_bucket", _ensure)
    return uploaded


@pytest.fixture
def mock_cbr_loaders(monkeypatch, tmp_path):
    import loader.cbr.cbr as cbr_loader
    from app.settings import get_settings

    data_root = tmp_path / "data"

    def _make_mock(name: str):
        async def _mock(first_date: str, last_date: str) -> int:
            out = data_root / "cbr" / name
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}_{first_date}_{last_date}.csv").write_text("col\n1\n2\n")
            return 42
        return _mock

    for name in ["key_rate", "refinancing_rate", "ruonia", "currency_rates",
                 "reserves", "metals_prices", "ibor", "roisfix"]:
        monkeypatch.setattr(cbr_loader, name, _make_mock(name))

    monkeypatch.setattr("app.settings.Settings.data_root", str(data_root), raising=False)
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_ROOT", str(data_root))
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_moex_loaders(monkeypatch, tmp_path):
    import loader.moex.algopack as moex_loader
    from app.settings import get_settings

    data_root = tmp_path / "data"

    def _make_mock_with_period(name: str):
        async def _mock(ticker: str, first_date: str, last_date: str, period=None) -> int:
            out = data_root / "moex" / name
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}_{ticker}_{first_date}_{last_date}.csv").write_text("col\n1\n2\n")
            return 42
        return _mock

    def _make_mock(name: str):
        async def _mock(ticker: str, first_date: str, last_date: str) -> int:
            out = data_root / "moex" / name
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}_{ticker}_{first_date}_{last_date}.csv").write_text("col\n1\n2\n")
            return 42
        return _mock

    monkeypatch.setattr(moex_loader, "shares", _make_mock_with_period("shares"))
    for name in ["orderbook", "tradestats", "orderstats", "indices", "ofz_curve", "derivatives"]:
        monkeypatch.setattr(moex_loader, name, _make_mock(name))

    monkeypatch.setenv("DATA_ROOT", str(data_root))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_rosstat_loaders(monkeypatch, tmp_path):
    import loader.rosstat.parsers as rosstat_loader
    from app.settings import get_settings

    data_root = tmp_path / "data"

    def _make_mock(name: str):
        async def _mock() -> int:
            out = data_root / "rosstat" / name
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.csv").write_text("col\n1\n2\n")
            return 42
        return _mock

    monkeypatch.setattr(rosstat_loader, "cpi", _make_mock("cpi"))
    monkeypatch.setattr(rosstat_loader, "ipp", _make_mock("ipp"))
    monkeypatch.setenv("DATA_ROOT", str(data_root))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_minfin_loaders(monkeypatch, tmp_path):
    import loader.minfin.parsers as minfin_loader
    from app.settings import get_settings

    data_root = tmp_path / "data"

    def _make_mock(name: str):
        async def _mock() -> int:
            out = data_root / "minfin" / name
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.csv").write_text("col\n1\n2\n")
            return 42
        return _mock

    for name in ["budget", "fnb", "ofz_auctions", "state_support"]:
        monkeypatch.setattr(minfin_loader, name, _make_mock(name))

    monkeypatch.setenv("DATA_ROOT", str(data_root))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    user_id = str(uuid.uuid4())[:8]
    reg_resp = await client.post("/auth/register", json={
        "username": f"testuser_{user_id}",
        "email": f"test_{user_id}@example.com",
        "password": "testpassword123",
    })
    assert reg_resp.status_code == 201, reg_resp.text

    login_resp = await client.post("/auth/login", json={
        "username": f"testuser_{user_id}",
        "password": "testpassword123",
    })
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
