"""
Named Entity Recognition — regex-based, rule-based, and entity linking.

WHY THIS MATTERS:
When a user says "Pick me up at 123 Main St at 3pm for about $25",
the chatbot needs to extract structured entities: LOCATION, TIME, AMOUNT.
NER turns unstructured text into actionable data that downstream systems
(routing, billing, scheduling) can consume.

Key concepts:
  - Regex NER: fast, precise for well-formatted entities (phone, email,
    dollar amounts, times). Fragile for free-form text.
  - Gazetteer: a lookup dictionary of known entities (city names, landmarks).
    Catches entities that don't follow patterns.
  - Entity linking: resolving "JFK" to "John F. Kennedy International Airport"
    by matching against a knowledge base of canonical names and aliases.
"""

import re
from enum import Enum
from dataclasses import dataclass, field


class EntityType(Enum):
    """Types of named entities recognized by the system."""
    LOCATION = "location"
    TIME = "time"
    AMOUNT = "amount"
    PERSON = "person"
    VEHICLE_TYPE = "vehicle_type"
    PHONE = "phone"
    EMAIL = "email"


@dataclass
class Entity:
    """A recognized named entity with its position in the source text.

    Attributes:
        text: the matched surface form (e.g., "$25.50")
        entity_type: the EntityType classification
        start: character offset where the entity begins
        end: character offset where the entity ends
        value: optional normalized value (e.g., 25.50 for "$25.50")
    """
    text: str
    entity_type: EntityType
    start: int
    end: int
    value: object = None


class RegexNER:
    """Regex-based Named Entity Recognition.

    Uses regular expressions to extract well-formatted entities like
    dollar amounts, times, phone numbers, and email addresses. This is
    the baseline NER approach — fast and precise but limited to patterns
    you explicitly define.
    """

    # Compiled patterns for each entity type
    _PATTERNS = [
        (EntityType.AMOUNT, re.compile(
            r'\$\d+\.?\d*'
            r'|\d+\.?\d*\s*dollars',
            re.IGNORECASE,
        )),
        (EntityType.TIME, re.compile(
            r'\d{1,2}:\d{2}\s*(?:am|pm)?'
            r'|\d{1,2}\s*(?:am|pm)',
            re.IGNORECASE,
        )),
        (EntityType.PHONE, re.compile(
            r'\d{3}[-.]?\d{3}[-.]?\d{4}',
        )),
        (EntityType.EMAIL, re.compile(
            r'[\w.-]+@[\w.-]+\.\w+',
        )),
    ]

    def extract(self, text: str) -> list[Entity]:
        """Extract entities from text using regex patterns.

        Scans text for AMOUNT, TIME, PHONE, and EMAIL patterns.
        Returns a list of Entity objects with character offsets.
        """
        entities: list[Entity] = []

        for entity_type, pattern in self._PATTERNS:
            for match in pattern.finditer(text):
                value = None
                matched_text = match.group()

                if entity_type == EntityType.AMOUNT:
                    # Normalize to float
                    numeric = re.findall(r'\d+\.?\d*', matched_text)
                    if numeric:
                        value = float(numeric[0])

                entities.append(Entity(
                    text=matched_text,
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    value=value,
                ))

        return entities


class RuleBasedNER:
    """Rule-based NER combining regex patterns and gazetteers.

    Extends RegexNER with gazetteer lookup — a dictionary of known
    entities like city names, landmarks, or vehicle types. This
    catches entities that don't follow regular patterns (e.g.,
    "Times Square" as a LOCATION).
    """

    def __init__(self):
        self._regex_ner = RegexNER()
        self._gazetteers: dict[EntityType, list[str]] = {}

    def add_gazetteer(self, entity_type: EntityType, terms: list[str]) -> None:
        """Add known entity terms for gazetteer matching.

        Terms are stored as-is; matching is case-insensitive.
        """
        if entity_type not in self._gazetteers:
            self._gazetteers[entity_type] = []
        self._gazetteers[entity_type].extend(terms)

    def extract(self, text: str) -> list[Entity]:
        """Extract entities using both regex and gazetteer matching.

        First applies regex patterns, then scans for gazetteer terms.
        Gazetteer matching is case-insensitive.
        """
        entities = self._regex_ner.extract(text)

        text_lower = text.lower()
        for entity_type, terms in self._gazetteers.items():
            for term in terms:
                term_lower = term.lower()
                start = 0
                while True:
                    idx = text_lower.find(term_lower, start)
                    if idx == -1:
                        break
                    entities.append(Entity(
                        text=text[idx:idx + len(term)],
                        entity_type=entity_type,
                        start=idx,
                        end=idx + len(term),
                    ))
                    start = idx + 1

        return entities


class EntityLinker:
    """Link extracted entities to canonical database entries.

    In a real system, "JFK", "Kennedy Airport", and "John F. Kennedy
    International Airport" should all resolve to the same canonical
    entity. EntityLinker maintains a mapping from aliases to canonical
    names.
    """

    def __init__(self):
        self._entities: dict[str, tuple[str, EntityType]] = {}  # alias_lower -> (canonical, type)

    def add_entity(
        self,
        canonical_name: str,
        entity_type: EntityType,
        aliases: list[str],
    ) -> None:
        """Register a canonical entity with its aliases.

        Each alias (case-insensitive) maps to the canonical name.
        The canonical name itself is also registered as an alias.
        """
        all_names = [canonical_name] + aliases
        for alias in all_names:
            self._entities[alias.lower()] = (canonical_name, entity_type)

    def link(self, entity: Entity) -> str | None:
        """Resolve an Entity to its canonical name.

        Returns the canonical name if the entity's text matches a
        known alias (case-insensitive), otherwise None.
        """
        key = entity.text.lower()
        if key in self._entities:
            canonical, _ = self._entities[key]
            return canonical
        return None
