from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse

from minio import Minio

from app.core.config import settings


class SourceStorage:
    def __init__(self) -> None:
        endpoint = urlparse(settings.s3_endpoint_url)
        if endpoint.scheme not in ("http", "https") or not endpoint.netloc:
            raise ValueError("对象存储地址必须是 HTTP 或 HTTPS URL")
        self.client = Minio(
            endpoint.netloc,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=endpoint.scheme == "https",
        )
        self.bucket = settings.s3_bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.ensure_bucket()
        self.client.put_object(
            self.bucket, key, BytesIO(data), len(data), content_type=content_type
        )

    def get(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            data = response.read(settings.source_max_bytes + 1)
            if len(data) > settings.source_max_bytes:
                raise ValueError("文件超过大小限制")
            return data
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        self.client.remove_object(self.bucket, key)


@lru_cache
def get_source_storage() -> SourceStorage:
    return SourceStorage()
