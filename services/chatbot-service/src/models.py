"""
Domain models for the Chatbot service.
"""


class ChatIntent:
    """A chat intent with patterns and responses."""

    def __init__(
        self,
        id: str,
        name: str,
        patterns: list[str],
        responses: list[str],
        priority: int,
    ):
        self.id = id
        self.name = name
        self.patterns = patterns
        self.responses = responses
        self.priority = priority

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "patterns": self.patterns,
            "responses": self.responses,
            "priority": self.priority,
        }


class Conversation:
    """A conversation session."""

    def __init__(
        self,
        id: str,
        user_id: str,
        messages: list[dict],
        status: str,
        started_at: str,
    ):
        self.id = id
        self.user_id = user_id
        self.messages = messages
        self.status = status
        self.started_at = started_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "messages": self.messages,
            "status": self.status,
            "started_at": self.started_at,
        }


class ChatMessage:
    """A single chat message."""

    def __init__(
        self,
        role: str,
        content: str,
        intent: str | None,
        entities: list,
        timestamp: str,
    ):
        self.role = role
        self.content = content
        self.intent = intent
        self.entities = entities
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "entities": self.entities,
            "timestamp": self.timestamp,
        }
