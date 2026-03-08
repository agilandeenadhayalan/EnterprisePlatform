"""
Tests for chat service — schema validation, config, and imports.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError


class TestChatRoomSchemas:
    """Verify Pydantic schema validation for chat room requests/responses."""

    def test_create_room_request_valid(self):
        from schemas import CreateRoomRequest
        req = CreateRoomRequest(
            participant_ids=["user-1", "user-2"],
            room_type="trip",
            trip_id="trip-123",
        )
        assert len(req.participant_ids) == 2
        assert req.room_type == "trip"

    def test_create_room_request_defaults(self):
        from schemas import CreateRoomRequest
        req = CreateRoomRequest(participant_ids=["user-1"])
        assert req.room_type == "trip"
        assert req.trip_id is None

    def test_create_room_request_requires_participants(self):
        from schemas import CreateRoomRequest
        with pytest.raises(ValidationError):
            CreateRoomRequest(participant_ids=[])

    def test_chat_room_response_valid(self):
        from schemas import ChatRoomResponse
        now = datetime.now(timezone.utc)
        resp = ChatRoomResponse(
            id="room-1",
            room_type="trip",
            participant_ids=["user-1", "user-2"],
            created_at=now,
        )
        assert resp.trip_id is None
        assert len(resp.participant_ids) == 2

    def test_chat_room_response_with_trip(self):
        from schemas import ChatRoomResponse
        now = datetime.now(timezone.utc)
        resp = ChatRoomResponse(
            id="room-1",
            trip_id="trip-123",
            room_type="trip",
            participant_ids=["user-1", "user-2"],
            created_at=now,
        )
        assert resp.trip_id == "trip-123"


class TestChatMessageSchemas:
    """Verify Pydantic schema validation for chat message requests/responses."""

    def test_send_message_request_valid(self):
        from schemas import SendMessageRequest
        req = SendMessageRequest(
            sender_id="user-1",
            message="Hello!",
        )
        assert req.message_type == "text"

    def test_send_message_request_custom_type(self):
        from schemas import SendMessageRequest
        req = SendMessageRequest(
            sender_id="user-1",
            message="https://maps.google.com/...",
            message_type="location",
        )
        assert req.message_type == "location"

    def test_chat_message_response_valid(self):
        from schemas import ChatMessageResponse
        now = datetime.now(timezone.utc)
        resp = ChatMessageResponse(
            id="msg-1",
            room_id="room-1",
            sender_id="user-1",
            message="Hello!",
            message_type="text",
            created_at=now,
        )
        assert resp.message == "Hello!"

    def test_chat_message_list_response(self):
        from schemas import ChatMessageResponse, ChatMessageListResponse
        now = datetime.now(timezone.utc)
        messages = [
            ChatMessageResponse(
                id=f"msg-{i}",
                room_id="room-1",
                sender_id="user-1",
                message=f"Message {i}",
                message_type="text",
                created_at=now,
            )
            for i in range(3)
        ]
        resp = ChatMessageListResponse(messages=messages, count=3)
        assert resp.count == 3

    def test_chat_message_list_empty(self):
        from schemas import ChatMessageListResponse
        resp = ChatMessageListResponse(messages=[], count=0)
        assert resp.count == 0


class TestChatConfig:
    """Verify chat service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "chat-service"
        assert settings.service_port == 8094

    def test_database_url_format(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
