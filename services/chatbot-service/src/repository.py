"""
In-memory chatbot repository with pre-seeded data.
"""

import uuid
import random
from datetime import datetime, timezone

from models import ChatIntent, Conversation, ChatMessage


class ChatbotRepository:
    """In-memory store for intents, conversations, and messages."""

    def __init__(self, seed: bool = False):
        self.intents: dict[str, ChatIntent] = {}
        self.conversations: dict[str, Conversation] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        intents = [
            ChatIntent("intent-001", "greeting", ["hello", "hi", "hey", "good morning"], ["Hello! How can I help you today?", "Hi there! What can I do for you?", "Welcome! How may I assist you?"], 10),
            ChatIntent("intent-002", "fare_inquiry", ["fare", "price", "cost", "how much"], ["You can check fares in the app under Pricing.", "Fares depend on distance and demand. Check the fare estimator!", "I can help with fare info. What route are you looking at?"], 5),
            ChatIntent("intent-003", "ride_status", ["where is my ride", "ride status", "track", "driver location"], ["Let me check your ride status.", "Your driver is on the way!", "I can track your ride. One moment please."], 8),
            ChatIntent("intent-004", "cancel_ride", ["cancel", "cancel ride", "stop ride", "don't want ride"], ["I can help you cancel. Note that cancellation fees may apply.", "Are you sure you want to cancel your ride?", "Your ride has been cancelled."], 7),
            ChatIntent("intent-005", "complaint", ["complaint", "problem", "issue", "bad experience"], ["I'm sorry to hear that. Let me help resolve your issue.", "We take your feedback seriously. Can you tell me more?", "I apologize for the inconvenience. Let me look into this."], 9),
            ChatIntent("intent-006", "payment_help", ["payment", "charge", "billing", "refund"], ["I can help with payment issues.", "Let me look into your billing concern.", "For refunds, I'll connect you with our billing team."], 6),
            ChatIntent("intent-007", "safety_info", ["safety", "emergency", "accident", "unsafe"], ["Your safety is our top priority. Tap the emergency button in the app.", "In an emergency, call 911 first, then use the in-app emergency button.", "I can connect you with our safety team right away."], 10),
            ChatIntent("intent-008", "goodbye", ["bye", "goodbye", "thanks", "thank you"], ["Goodbye! Have a great day!", "Thanks for chatting! Bye!", "You're welcome! Don't hesitate to reach out again."], 1),
        ]
        for intent in intents:
            self.intents[intent.id] = intent

        conversations = [
            Conversation("conv-001", "user-A", [
                {"role": "user", "content": "Hello", "intent": "greeting", "entities": [], "timestamp": now},
                {"role": "bot", "content": "Hello! How can I help you today?", "intent": None, "entities": [], "timestamp": now},
            ], "active", now),
            Conversation("conv-002", "user-B", [
                {"role": "user", "content": "How much is a ride to JFK?", "intent": "fare_inquiry", "entities": [], "timestamp": now},
                {"role": "bot", "content": "Fares depend on distance and demand. Check the fare estimator!", "intent": None, "entities": [], "timestamp": now},
            ], "active", now),
            Conversation("conv-003", "user-C", [
                {"role": "user", "content": "Thanks bye", "intent": "goodbye", "entities": [], "timestamp": now},
                {"role": "bot", "content": "Goodbye! Have a great day!", "intent": None, "entities": [], "timestamp": now},
            ], "closed", now),
            Conversation("conv-004", "user-D", [
                {"role": "user", "content": "I had a bad experience", "intent": "complaint", "entities": [], "timestamp": now},
                {"role": "bot", "content": "I'm sorry to hear that. Let me help resolve your issue.", "intent": None, "entities": [], "timestamp": now},
                {"role": "user", "content": "The driver was rude", "intent": "complaint", "entities": [], "timestamp": now},
            ], "escalated", now),
        ]
        for conv in conversations:
            self.conversations[conv.id] = conv

    # ── Intent matching ──

    def match_intent(self, message: str) -> ChatIntent | None:
        msg_lower = message.lower()
        best_intent = None
        best_score = 0
        for intent in self.intents.values():
            score = sum(1 for pattern in intent.patterns if pattern in msg_lower)
            if score > best_score:
                best_score = score
                best_intent = intent
            elif score == best_score and score > 0 and best_intent and intent.priority > best_intent.priority:
                best_intent = intent
        return best_intent

    # ── Messages ──

    def send_message(self, user_id: str, message: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()

        # Find or create active conversation
        conv = None
        for c in self.conversations.values():
            if c.user_id == user_id and c.status == "active":
                conv = c
                break

        if not conv:
            conv_id = f"conv-{uuid.uuid4().hex[:8]}"
            conv = Conversation(conv_id, user_id, [], "active", now)
            self.conversations[conv.id] = conv

        # Match intent
        intent = self.match_intent(message)
        intent_name = intent.name if intent else None

        user_msg = ChatMessage("user", message, intent_name, [], now)
        conv.messages.append(user_msg.to_dict())

        # Generate response
        if intent:
            response_text = random.choice(intent.responses)
        else:
            response_text = "I'm not sure I understand. Could you rephrase that?"

        bot_msg = ChatMessage("bot", response_text, None, [], now)
        conv.messages.append(bot_msg.to_dict())

        return {
            "conversation_id": conv.id,
            "user_message": user_msg.to_dict(),
            "bot_response": bot_msg.to_dict(),
            "matched_intent": intent_name,
        }

    # ── Conversations ──

    def list_conversations(self, user_id: str | None = None, status: str | None = None) -> list[Conversation]:
        result = list(self.conversations.values())
        if user_id:
            result = [c for c in result if c.user_id == user_id]
        if status:
            result = [c for c in result if c.status == status]
        return result

    def get_conversation(self, conv_id: str) -> Conversation | None:
        return self.conversations.get(conv_id)

    def close_conversation(self, conv_id: str) -> Conversation | None:
        conv = self.conversations.get(conv_id)
        if conv:
            conv.status = "closed"
        return conv

    # ── Intents ──

    def list_intents(self) -> list[ChatIntent]:
        return list(self.intents.values())

    def get_intent(self, intent_id: str) -> ChatIntent | None:
        return self.intents.get(intent_id)

    def create_intent(self, data: dict) -> ChatIntent:
        intent_id = f"intent-{uuid.uuid4().hex[:8]}"
        intent = ChatIntent(
            id=intent_id,
            name=data["name"],
            patterns=data["patterns"],
            responses=data["responses"],
            priority=data.get("priority", 1),
        )
        self.intents[intent.id] = intent
        return intent

    # ── Stats ──

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        total_messages = 0
        intent_counts: dict[str, int] = {}
        for c in self.conversations.values():
            by_status[c.status] = by_status.get(c.status, 0) + 1
            total_messages += len(c.messages)
            for msg in c.messages:
                if msg.get("intent"):
                    intent_counts[msg["intent"]] = intent_counts.get(msg["intent"], 0) + 1

        top_intents = sorted(
            [{"intent": k, "count": v} for k, v in intent_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        return {
            "total_conversations": len(self.conversations),
            "by_status": by_status,
            "total_messages": total_messages,
            "top_intents": top_intents,
        }


REPO_CLASS = ChatbotRepository
repo = ChatbotRepository(seed=True)
