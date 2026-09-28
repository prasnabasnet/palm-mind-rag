import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


class DocumentRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def save(self, document: Document) -> Document:
        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def get(self, document_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, document_id)

    async def list_documents(self, limit: int, offset: int) -> list[Document]:
        result = await self._session.scalars(
            select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result)

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.commit()