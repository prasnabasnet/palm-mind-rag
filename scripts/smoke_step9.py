import asyncio

import httpx

BASE_URL = "http://localhost:8000/api/v1/chat"
SESSION_ID = "smoke-e2e"


async def send(client: httpx.AsyncClient, message: str) -> None:
    response = await client.post(
        BASE_URL, json={"session_id": SESSION_ID, "message": message}
    )
    response.raise_for_status()
    body = response.json()
    print(f"\nYou: {message}")
    print(f"Bot: {body['reply']}")
    if body["booking_confirmed"]:
        print("   (booking confirmed)")


async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        await send(client, "How many days of annual leave do employees get?")
        await send(client, "And how many of those can I carry over?")

        await send(client, "I'd like to book an interview")
        await send(client, "My name is Prasna Basnet")
        await send(client, "My email is prasna@example.com")
        await send(client, "October 5th 2026")
        await send(client, "2pm")


if __name__ == "__main__":
    asyncio.run(main())