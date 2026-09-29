

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_chat_service
from app.api.v1.routes import chat
from app.schemas.chat import SourceReference
from app.services.chat_service import ChatTurnResult


class FakeChatService:
    async def handle_message(self, session_id: str, message: str) -> ChatTurnResult:
        return ChatTurnResult(
            reply=f"echo: {message}",
            sources=[
                SourceReference(
                    document_id="11111111-1111-1111-1111-111111111111",  # type: ignore[arg-type]
                    filename="policy.txt",
                    chunk_index=0,
                    score=0.9,
                )
            ],
            booking_confirmed=False,
        )


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(chat.router, prefix="/api/v1")
    test_app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    return test_app


async def test_chat_endpoint_returns_reply_and_sources(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat", json={"session_id": "s1", "message": "hello"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "echo: hello"
    assert body["sources"][0]["filename"] == "policy.txt"
    assert body["booking_confirmed"] is False


async def test_chat_endpoint_rejects_empty_message(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"session_id": "s1", "message": ""})

    assert response.status_code == 422