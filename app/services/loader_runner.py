import inspect
import json
import uuid
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import user_request as request_crud
from app.exceptions import LoaderError
from app.services.minio_client import upload_file
from app.settings import get_settings


def _json_safe(v: object) -> bool:
    try:
        json.dumps(v)
        return True
    except TypeError:
        return False


async def run_loader(
    loader_fn: Callable[..., Coroutine[Any, Any, int]],
    loader_kwargs: dict,
    source: str,
    endpoint: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    settings = get_settings()
    subdir = Path(settings.data_root) / source / endpoint
    subdir.mkdir(parents=True, exist_ok=True)

    # Clear scratch dir so we only see files produced by this run
    for f in subdir.glob("*.csv"):
        f.unlink()

    if inspect.iscoroutinefunction(loader_fn):
        rows = await loader_fn(**loader_kwargs)
    else:
        rows = loader_fn(**loader_kwargs)
    if not rows:
        raise LoaderError(f"{source}/{endpoint} returned 0 rows — upstream may be unavailable")

    uploaded: list[str] = []
    for local_file in subdir.glob("*.csv"):
        object_key = f"{source}/{endpoint}/{local_file.name}"
        await upload_file(str(local_file), object_key)
        local_file.unlink()
        uploaded.append(object_key)

    log_params = {k: v if _json_safe(v) else str(v) for k, v in loader_kwargs.items()}
    await request_crud.create_log(db, user_id, source, endpoint, rows, log_params)
    return {"rows_downloaded": rows, "files": uploaded}
