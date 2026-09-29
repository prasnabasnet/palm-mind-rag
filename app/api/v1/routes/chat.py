from fastapi import APIRouter, status

from app.api.deps import ChatServiceDep
from app.schemas.chat_api import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(request: ChatRequest, service: ChatServiceDep) -> ChatResponse:
    result = await service.handle_message(request.session_id, request.message)
    return ChatResponse(
        session_id=request.session_id,
        reply=result.reply,
        sources=result.sources,
        booking_confirmed=result.booking_confirmed,
    )