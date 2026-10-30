import httpx

from app.config import Settings


class VoyageEmbedder:
    URL = "https://api.voyageai.com/v1/embeddings"

    def __init__(self, settings: Settings):
        self._model = settings.embedding_model
        self._dim = settings.embedding_dim
        self._client = httpx.AsyncClient(
            timeout=15, headers={"Authorization": f"Bearer {settings.embedding_api_key}"}
        )

    async def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        resp = await self._client.post(
            self.URL,
            json={
                "input": texts,
                "model": self._model,
                "input_type": "query" if is_query else "document",
                "output_dimension": self._dim,
            },
        )
        resp.raise_for_status()
        return [d["embedding"] for d in resp.json()["data"]]

    async def close(self) -> None:
        await self._client.aclose()


def make_embedder(settings: Settings) -> VoyageEmbedder | None:
    if settings.embedding_provider == "voyage" and settings.embedding_api_key:
        return VoyageEmbedder(settings)
    return None
