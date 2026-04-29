import aioboto3
from botocore.exceptions import ClientError

from app.exceptions import MinIOError
from app.settings import get_settings

_session = aioboto3.Session()


def _client_kwargs() -> dict:
    s = get_settings()
    return {
        "endpoint_url": f"{'https' if s.minio_use_ssl else 'http'}://{s.minio_endpoint}",
        "aws_access_key_id": s.minio_access_key,
        "aws_secret_access_key": s.minio_secret_key,
    }


async def ensure_bucket(bucket: str) -> None:
    async with _session.client("s3", **_client_kwargs()) as s3:
        try:
            await s3.head_bucket(Bucket=bucket)
        except ClientError:
            await s3.create_bucket(Bucket=bucket)


async def upload_file(local_path: str, object_key: str) -> None:
    s = get_settings()
    try:
        async with _session.client("s3", **_client_kwargs()) as s3:
            await s3.upload_file(local_path, s.minio_bucket, object_key)
    except ClientError as e:
        raise MinIOError(f"Failed to upload {object_key}: {e}") from e
