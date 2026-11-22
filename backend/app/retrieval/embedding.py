import math

import httpx

from app.core.config import settings


class EmbeddingClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if settings.embedding_dimensions != 768:
            raise ValueError("当前数据库向量维度为 768；更换维度须先修改迁移与模型")
        headers = (
            {"Authorization": f"Bearer {settings.embedding_api_key}"}
            if settings.embedding_api_key
            else {}
        )
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(
            base_url=settings.embedding_base_url.rstrip("/") + "/", timeout=60
        ) as client:
            for start in range(0, len(texts), 16):
                batch = texts[start : start + 16]
                response = await client.post(
                    "embeddings",
                    json={"model": settings.embedding_model, "input": batch},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                data = sorted(payload["data"], key=lambda item: item["index"])
                if len(data) != len(batch) or [item["index"] for item in data] != list(
                    range(len(batch))
                ):
                    raise ValueError("Embedding 服务返回的向量数量不匹配")
                for item in data:
                    vector = item["embedding"]
                    if (
                        len(vector) != 768
                        or not all(
                            isinstance(value, (float, int)) and math.isfinite(value)
                            for value in vector
                        )
                        or not any(value != 0 for value in vector)
                    ):
                        raise ValueError("Embedding 服务返回的向量维度或数值无效")
                    vectors.append(vector)
        return vectors
