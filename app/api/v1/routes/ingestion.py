import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import IngestionServiceDep, SettingsDep
from app.core.enums import ChunkingStrategy
from app.schemas.document import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    service: IngestionServiceDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="A .pdf or .txt file")],
    strategy: Annotated[ChunkingStrategy, Form()] = ChunkingStrategy.FIXED,
) -> DocumentResponse:
    # Read one byte past the limit so oversized files are detected without loading them fully.
    data = await file.read(settings.max_upload_bytes + 1)
    document = await service.ingest(
        filename=file.filename or "",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        strategy=strategy,
    )
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    service: IngestionServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentResponse]:
    documents = await service.list_documents(limit, offset)
    return [DocumentResponse.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, service: IngestionServiceDep) -> DocumentResponse:
    return DocumentResponse.model_validate(await service.get_document(document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, service: IngestionServiceDep) -> None:
    await service.delete_document(document_id)