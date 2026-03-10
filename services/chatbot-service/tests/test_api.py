"""
Tests for the Chatbot service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_send_message(client: AsyncClient):
    payload = {"user_id": "user-new", "message": "hello there"}
    resp = await client.post("/chatbot/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert "bot_response" in data


@pytest.mark.anyio
async def test_message_matches_intent(client: AsyncClient):
    payload = {"user_id": "user-new", "message": "how much does it cost"}
    resp = await client.post("/chatbot/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_intent"] == "fare_inquiry"


@pytest.mark.anyio
async def test_message_creates_conversation(client: AsyncClient):
    payload = {"user_id": "user-brand-new", "message": "hello"}
    resp = await client.post("/chatbot/message", json=payload)
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]
    # Verify conversation exists
    conv_resp = await client.get(f"/chatbot/conversations/{conv_id}")
    assert conv_resp.status_code == 200


@pytest.mark.anyio
async def test_message_reuses_conversation(client: AsyncClient):
    # user-A already has an active conversation (conv-001)
    payload = {"user_id": "user-A", "message": "how much is a ride"}
    resp = await client.post("/chatbot/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == "conv-001"


@pytest.mark.anyio
async def test_list_conversations(client: AsyncClient):
    resp = await client.get("/chatbot/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["conversations"]) == 4


@pytest.mark.anyio
async def test_filter_user(client: AsyncClient):
    resp = await client.get("/chatbot/conversations", params={"user_id": "user-A"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["conversations"][0]["user_id"] == "user-A"


@pytest.mark.anyio
async def test_filter_status(client: AsyncClient):
    resp = await client.get("/chatbot/conversations", params={"status": "active"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for c in data["conversations"]:
        assert c["status"] == "active"


@pytest.mark.anyio
async def test_get_conversation(client: AsyncClient):
    resp = await client.get("/chatbot/conversations/conv-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-A"
    assert len(data["messages"]) >= 2


@pytest.mark.anyio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/chatbot/conversations/conv-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_close_conversation(client: AsyncClient):
    resp = await client.post("/chatbot/conversations/conv-001/close")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"


@pytest.mark.anyio
async def test_close_not_found(client: AsyncClient):
    resp = await client.post("/chatbot/conversations/conv-999/close")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_intents(client: AsyncClient):
    resp = await client.get("/chatbot/intents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["intents"]) == 8


@pytest.mark.anyio
async def test_create_intent(client: AsyncClient):
    payload = {
        "name": "weather_info",
        "patterns": ["weather", "rain", "sunny"],
        "responses": ["Check the weather forecast in the app."],
        "priority": 3,
    }
    resp = await client.post("/chatbot/intents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "weather_info"
    assert len(data["patterns"]) == 3


@pytest.mark.anyio
async def test_get_intent(client: AsyncClient):
    resp = await client.get("/chatbot/intents/intent-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "greeting"


@pytest.mark.anyio
async def test_intent_not_found(client: AsyncClient):
    resp = await client.get("/chatbot/intents/intent-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/chatbot/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_conversations"] == 4
    assert data["total_messages"] > 0


@pytest.mark.anyio
async def test_stats_top_intents(client: AsyncClient):
    resp = await client.get("/chatbot/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_intents" in data
    assert isinstance(data["top_intents"], list)
    assert len(data["top_intents"]) > 0
    assert "intent" in data["top_intents"][0]
    assert "count" in data["top_intents"][0]
