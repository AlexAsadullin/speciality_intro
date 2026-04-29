import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_request import UserRequest


async def create_log(
    db: AsyncSession,
    user_id: uuid.UUID,
    source: str,
    endpoint: str,
    rows_downloaded: int,
    parameters: dict | None,
) -> UserRequest:
    record = UserRequest(
        user_id=user_id,
        source=source,
        endpoint=endpoint,
        rows_downloaded=rows_downloaded,
        parameters=parameters,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
