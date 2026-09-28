import asyncio

from fastembed import TextEmbedding


class FastEmbedEmbedder:

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model = TextEmbedding(model_name=model_name)
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._embed_documents_sync, texts)

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_query_sync, text)

    def _embed_documents_sync(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = [v.tolist() for v in self._model.passage_embed(texts)]
        return vectors

    def _embed_query_sync(self, text: str) -> list[float]:
            vector: list[float] = next(iter(self._model.query_embed(text))).tolist()
            return vector