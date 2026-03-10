"""
Tests for M34: NLP & Chatbot — Intent classification, NER, and RAG.
"""

import pytest

from m34_nlp_chatbot.intent_classifier import (
    IntentType,
    KeywordMatcher,
    TFIDFClassifier,
    MultiIntentDetector,
)
from m34_nlp_chatbot.named_entity import (
    EntityType,
    Entity,
    RegexNER,
    RuleBasedNER,
    EntityLinker,
)
from m34_nlp_chatbot.rag_retriever import (
    Document,
    DocumentChunker,
    TFIDFRetriever,
    BM25Reranker,
    ContextAssembler,
)


# ── KeywordMatcher ──


class TestKeywordMatcher:
    def test_no_intents_returns_unknown(self):
        """Empty matcher returns UNKNOWN with 0.0 confidence."""
        matcher = KeywordMatcher()
        intent, conf = matcher.match("hello")
        assert intent == IntentType.UNKNOWN
        assert conf == 0.0

    def test_single_keyword_match(self):
        """Single keyword match yields partial confidence."""
        matcher = KeywordMatcher()
        matcher.add_intent(IntentType.GREETING, ["hello", "hi", "hey"])
        intent, conf = matcher.match("hello there")
        assert intent == IntentType.GREETING
        assert conf == pytest.approx(1 / 3)

    def test_all_keywords_match(self):
        """All keywords matching gives confidence 1.0."""
        matcher = KeywordMatcher()
        matcher.add_intent(IntentType.GREETING, ["hello", "hi"])
        intent, conf = matcher.match("hello hi")
        assert intent == IntentType.GREETING
        assert conf == 1.0

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        matcher = KeywordMatcher()
        matcher.add_intent(IntentType.RIDE_REQUEST, ["book", "ride"])
        intent, conf = matcher.match("BOOK a RIDE")
        assert intent == IntentType.RIDE_REQUEST
        assert conf == 1.0

    def test_multiple_intents_best_wins(self):
        """When multiple intents match, highest confidence wins."""
        matcher = KeywordMatcher()
        matcher.add_intent(IntentType.GREETING, ["hello", "hi", "hey", "greetings"])
        matcher.add_intent(IntentType.RIDE_REQUEST, ["book", "ride"])
        intent, conf = matcher.match("book a ride")
        assert intent == IntentType.RIDE_REQUEST
        assert conf == 1.0

    def test_no_keywords_match(self):
        """No matching keywords returns UNKNOWN."""
        matcher = KeywordMatcher()
        matcher.add_intent(IntentType.GREETING, ["hello"])
        intent, conf = matcher.match("xyz abc")
        assert intent == IntentType.UNKNOWN
        assert conf == 0.0

    def test_partial_keyword_match(self):
        """Substring matching works for keywords embedded in text."""
        matcher = KeywordMatcher()
        matcher.add_intent(IntentType.FARE_INQUIRY, ["fare", "cost", "price"])
        intent, conf = matcher.match("what is the fare for this trip?")
        assert intent == IntentType.FARE_INQUIRY
        assert conf == pytest.approx(1 / 3)


# ── TFIDFClassifier ──


class TestTFIDFClassifier:
    def _build_classifier(self):
        """Build a classifier with training documents."""
        clf = TFIDFClassifier()
        clf.add_document(IntentType.RIDE_REQUEST, "book a ride to the airport")
        clf.add_document(IntentType.RIDE_REQUEST, "I need a car to downtown")
        clf.add_document(IntentType.FARE_INQUIRY, "how much does a ride cost")
        clf.add_document(IntentType.FARE_INQUIRY, "what is the fare to the airport")
        clf.add_document(IntentType.GREETING, "hello how are you")
        clf.add_document(IntentType.COMPLAINT, "the driver was rude and late")
        return clf

    def test_no_documents_returns_unknown(self):
        """Empty classifier returns UNKNOWN."""
        clf = TFIDFClassifier()
        intent, score = clf.classify("hello")
        assert intent == IntentType.UNKNOWN
        assert score == 0.0

    def test_classify_ride_request(self):
        """Classifies ride booking query correctly."""
        clf = self._build_classifier()
        intent, score = clf.classify("book a ride")
        assert intent == IntentType.RIDE_REQUEST
        assert score > 0.0

    def test_classify_fare_inquiry(self):
        """Classifies fare question correctly."""
        clf = self._build_classifier()
        intent, score = clf.classify("how much does it cost")
        assert intent == IntentType.FARE_INQUIRY
        assert score > 0.0

    def test_classify_greeting(self):
        """Classifies greeting correctly."""
        clf = self._build_classifier()
        intent, score = clf.classify("hello there")
        assert intent == IntentType.GREETING
        assert score > 0.0

    def test_classify_complaint(self):
        """Classifies complaint correctly."""
        clf = self._build_classifier()
        intent, score = clf.classify("the driver was very rude")
        assert intent == IntentType.COMPLAINT
        assert score > 0.0

    def test_cosine_similarity_identical(self):
        """Identical vectors have cosine similarity 1.0."""
        clf = TFIDFClassifier()
        vec = {"a": 1.0, "b": 2.0}
        assert clf._cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors have cosine similarity 0.0."""
        clf = TFIDFClassifier()
        v1 = {"a": 1.0}
        v2 = {"b": 1.0}
        assert clf._cosine_similarity(v1, v2) == 0.0

    def test_cosine_similarity_empty(self):
        """Empty vectors return 0.0."""
        clf = TFIDFClassifier()
        assert clf._cosine_similarity({}, {"a": 1.0}) == 0.0

    def test_tfidf_computation(self):
        """TF-IDF produces non-negative weights."""
        clf = TFIDFClassifier()
        clf.add_document(IntentType.GREETING, "hello world")
        clf.add_document(IntentType.FAREWELL, "goodbye world")
        vec = clf._compute_tfidf("hello world")
        assert all(v >= 0 for v in vec.values())

    def test_tfidf_rare_word_higher_weight(self):
        """Rare words get higher TF-IDF weight than common words."""
        clf = TFIDFClassifier()
        clf.add_document(IntentType.GREETING, "hello world")
        clf.add_document(IntentType.FAREWELL, "goodbye world")
        vec = clf._compute_tfidf("hello world")
        # "hello" appears in 1 doc, "world" appears in 2 docs
        # "hello" should have higher IDF
        assert vec.get("hello", 0) > vec.get("world", 0)


# ── MultiIntentDetector ──


class TestMultiIntentDetector:
    def _build_classifier(self):
        clf = TFIDFClassifier()
        clf.add_document(IntentType.RIDE_REQUEST, "book a ride to the airport")
        clf.add_document(IntentType.FARE_INQUIRY, "how much does a ride cost to go there")
        clf.add_document(IntentType.GREETING, "hello how are you doing today")
        return clf

    def test_single_intent(self):
        """Single-sentence message returns one intent."""
        clf = self._build_classifier()
        detector = MultiIntentDetector()
        results = detector.detect("book a ride", clf, threshold=0.01)
        assert len(results) >= 1
        intents = [r[0] for r in results]
        assert IntentType.RIDE_REQUEST in intents

    def test_multiple_intents(self):
        """Multi-sentence message can return multiple intents."""
        clf = self._build_classifier()
        detector = MultiIntentDetector()
        results = detector.detect(
            "Book a ride to the airport. How much does it cost?",
            clf,
            threshold=0.01,
        )
        assert len(results) >= 2

    def test_empty_text(self):
        """Empty text returns no intents."""
        clf = self._build_classifier()
        detector = MultiIntentDetector()
        results = detector.detect("", clf)
        assert results == []

    def test_threshold_filters(self):
        """High threshold filters out low-confidence intents."""
        clf = self._build_classifier()
        detector = MultiIntentDetector()
        results = detector.detect("xyz random words", clf, threshold=0.99)
        assert results == []


# ── RegexNER ──


class TestRegexNER:
    def test_extract_dollar_amount(self):
        """Extracts $X.XX amounts."""
        ner = RegexNER()
        entities = ner.extract("The fare is $25.50 for this trip")
        amounts = [e for e in entities if e.entity_type == EntityType.AMOUNT]
        assert len(amounts) == 1
        assert amounts[0].text == "$25.50"
        assert amounts[0].value == 25.50

    def test_extract_dollar_amount_no_cents(self):
        """Extracts $X without decimal."""
        ner = RegexNER()
        entities = ner.extract("Pay $10 now")
        amounts = [e for e in entities if e.entity_type == EntityType.AMOUNT]
        assert len(amounts) == 1
        assert amounts[0].value == 10.0

    def test_extract_dollars_word(self):
        """Extracts 'N dollars' format."""
        ner = RegexNER()
        entities = ner.extract("It costs 15 dollars")
        amounts = [e for e in entities if e.entity_type == EntityType.AMOUNT]
        assert len(amounts) >= 1

    def test_extract_time_with_colon(self):
        """Extracts HH:MM format."""
        ner = RegexNER()
        entities = ner.extract("Pick me up at 3:30 pm")
        times = [e for e in entities if e.entity_type == EntityType.TIME]
        assert len(times) >= 1

    def test_extract_time_with_ampm(self):
        """Extracts 'N am/pm' format."""
        ner = RegexNER()
        entities = ner.extract("Meeting at 5pm")
        times = [e for e in entities if e.entity_type == EntityType.TIME]
        assert len(times) >= 1

    def test_extract_phone(self):
        """Extracts phone numbers."""
        ner = RegexNER()
        entities = ner.extract("Call me at 555-123-4567")
        phones = [e for e in entities if e.entity_type == EntityType.PHONE]
        assert len(phones) == 1
        assert "555" in phones[0].text

    def test_extract_phone_no_dashes(self):
        """Extracts phone without separators."""
        ner = RegexNER()
        entities = ner.extract("My number is 5551234567")
        phones = [e for e in entities if e.entity_type == EntityType.PHONE]
        assert len(phones) == 1

    def test_extract_email(self):
        """Extracts email addresses."""
        ner = RegexNER()
        entities = ner.extract("Email me at user@example.com")
        emails = [e for e in entities if e.entity_type == EntityType.EMAIL]
        assert len(emails) == 1
        assert emails[0].text == "user@example.com"

    def test_extract_multiple_entities(self):
        """Extracts multiple entity types from one text."""
        ner = RegexNER()
        entities = ner.extract("Pick me up at 3:30pm, fare is $25, call 555-111-2222")
        types = {e.entity_type for e in entities}
        assert EntityType.TIME in types
        assert EntityType.AMOUNT in types
        assert EntityType.PHONE in types

    def test_entity_spans(self):
        """Entity start/end offsets are correct."""
        ner = RegexNER()
        text = "Cost is $50 today"
        entities = ner.extract(text)
        amounts = [e for e in entities if e.entity_type == EntityType.AMOUNT]
        assert len(amounts) == 1
        assert text[amounts[0].start:amounts[0].end] == "$50"


# ── RuleBasedNER ──


class TestRuleBasedNER:
    def test_gazetteer_match(self):
        """Gazetteer finds known locations."""
        ner = RuleBasedNER()
        ner.add_gazetteer(EntityType.LOCATION, ["Times Square", "Central Park"])
        entities = ner.extract("Take me to Times Square")
        locations = [e for e in entities if e.entity_type == EntityType.LOCATION]
        assert len(locations) == 1
        assert locations[0].text == "Times Square"

    def test_gazetteer_case_insensitive(self):
        """Gazetteer matching is case-insensitive."""
        ner = RuleBasedNER()
        ner.add_gazetteer(EntityType.LOCATION, ["Wall Street"])
        entities = ner.extract("head to wall street please")
        locations = [e for e in entities if e.entity_type == EntityType.LOCATION]
        assert len(locations) == 1

    def test_combined_regex_and_gazetteer(self):
        """RuleBasedNER combines regex and gazetteer results."""
        ner = RuleBasedNER()
        ner.add_gazetteer(EntityType.LOCATION, ["JFK Airport"])
        entities = ner.extract("Take me to JFK Airport, fare is $45")
        types = {e.entity_type for e in entities}
        assert EntityType.LOCATION in types
        assert EntityType.AMOUNT in types

    def test_gazetteer_vehicle_type(self):
        """Gazetteer works for vehicle types."""
        ner = RuleBasedNER()
        ner.add_gazetteer(EntityType.VEHICLE_TYPE, ["SUV", "sedan", "luxury"])
        entities = ner.extract("I need an SUV please")
        vehicles = [e for e in entities if e.entity_type == EntityType.VEHICLE_TYPE]
        assert len(vehicles) == 1


# ── EntityLinker ──


class TestEntityLinker:
    def test_link_alias(self):
        """Links alias to canonical name."""
        linker = EntityLinker()
        linker.add_entity("John F. Kennedy International Airport", EntityType.LOCATION, ["JFK", "Kennedy Airport"])
        entity = Entity("JFK", EntityType.LOCATION, 0, 3)
        result = linker.link(entity)
        assert result == "John F. Kennedy International Airport"

    def test_link_canonical(self):
        """Links canonical name to itself."""
        linker = EntityLinker()
        linker.add_entity("Grand Central", EntityType.LOCATION, ["GCT"])
        entity = Entity("Grand Central", EntityType.LOCATION, 0, 13)
        result = linker.link(entity)
        assert result == "Grand Central"

    def test_link_unknown(self):
        """Unknown entity returns None."""
        linker = EntityLinker()
        linker.add_entity("JFK Airport", EntityType.LOCATION, ["JFK"])
        entity = Entity("LAX", EntityType.LOCATION, 0, 3)
        result = linker.link(entity)
        assert result is None

    def test_link_case_insensitive(self):
        """Linking is case-insensitive."""
        linker = EntityLinker()
        linker.add_entity("Penn Station", EntityType.LOCATION, ["penn", "penn station"])
        entity = Entity("PENN", EntityType.LOCATION, 0, 4)
        result = linker.link(entity)
        assert result == "Penn Station"


# ── DocumentChunker ──


class TestDocumentChunker:
    def test_short_document_single_chunk(self):
        """Short document produces a single chunk."""
        chunker = DocumentChunker()
        doc = Document("d1", "Test", "one two three")
        chunks = chunker.chunk(doc, chunk_size=10)
        assert len(chunks) == 1
        assert chunks[0]["word_count"] == 3
        assert chunks[0]["doc_id"] == "d1"

    def test_chunking_produces_overlap(self):
        """Overlapping chunks share words."""
        chunker = DocumentChunker()
        content = " ".join(f"word{i}" for i in range(20))
        doc = Document("d1", "Test", content)
        chunks = chunker.chunk(doc, chunk_size=10, overlap=5)
        assert len(chunks) >= 2
        # Second chunk should start 5 words into the first
        words1 = set(chunks[0]["text"].split())
        words2 = set(chunks[1]["text"].split())
        assert len(words1 & words2) > 0  # Some overlap

    def test_chunk_indices_sequential(self):
        """Chunk indices are sequential starting from 0."""
        chunker = DocumentChunker()
        content = " ".join(f"w{i}" for i in range(30))
        doc = Document("d1", "Test", content)
        chunks = chunker.chunk(doc, chunk_size=10, overlap=0)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_document(self):
        """Empty document produces no chunks."""
        chunker = DocumentChunker()
        doc = Document("d1", "Test", "")
        chunks = chunker.chunk(doc)
        assert chunks == []


# ── TFIDFRetriever ──


class TestTFIDFRetriever:
    def _build_index(self):
        chunker = DocumentChunker()
        docs = [
            Document("d1", "Pricing", "ride pricing fare cost estimation algorithm"),
            Document("d2", "Safety", "safety features emergency contact driver verification"),
            Document("d3", "Booking", "how to book a ride request pickup drop off"),
        ]
        all_chunks = []
        for doc in docs:
            all_chunks.extend(chunker.chunk(doc, chunk_size=50))
        retriever = TFIDFRetriever()
        retriever.index(all_chunks)
        return retriever

    def test_retrieve_relevant(self):
        """Retrieves relevant chunks for a query."""
        retriever = self._build_index()
        results = retriever.retrieve("how much does a ride cost", top_k=3)
        assert len(results) <= 3
        assert results[0]["score"] > 0

    def test_retrieve_top_k(self):
        """Returns at most top_k results."""
        retriever = self._build_index()
        results = retriever.retrieve("ride", top_k=2)
        assert len(results) <= 2

    def test_retrieve_has_score(self):
        """Each result has a 'score' key."""
        retriever = self._build_index()
        results = retriever.retrieve("safety")
        for r in results:
            assert "score" in r

    def test_empty_retriever(self):
        """Empty index returns empty results."""
        retriever = TFIDFRetriever()
        results = retriever.retrieve("anything")
        assert results == []

    def test_retrieve_sorted_by_score(self):
        """Results are sorted by descending score."""
        retriever = self._build_index()
        results = retriever.retrieve("ride cost pricing")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ── BM25Reranker ──


class TestBM25Reranker:
    def test_bm25_score_positive(self):
        """BM25 scores are positive when query terms appear in document."""
        reranker = BM25Reranker()
        score = reranker.score("ride cost", "the cost of a ride to the airport")
        assert score > 0

    def test_bm25_score_zero_no_match(self):
        """BM25 score is 0 when no query terms match."""
        reranker = BM25Reranker()
        score = reranker.score("xyz abc", "the cost of a ride")
        assert score == 0.0

    def test_bm25_rerank(self):
        """Rerank returns top-k chunks sorted by BM25 score."""
        reranker = BM25Reranker()
        chunks = [
            {"text": "safety features and emergency contact"},
            {"text": "ride cost fare pricing estimation"},
            {"text": "how to book a ride request"},
        ]
        results = reranker.rerank("ride cost", chunks, top_k=2)
        assert len(results) == 2
        assert "bm25_score" in results[0]
        assert results[0]["bm25_score"] >= results[1]["bm25_score"]

    def test_bm25_empty_chunks(self):
        """Empty chunk list returns empty results."""
        reranker = BM25Reranker()
        results = reranker.rerank("query", [])
        assert results == []


# ── ContextAssembler ──


class TestContextAssembler:
    def test_assemble_basic(self):
        """Assembles context from chunks."""
        assembler = ContextAssembler()
        chunks = [
            {"text": "chunk one content here"},
            {"text": "chunk two content here"},
        ]
        ctx = assembler.assemble("query", chunks, max_tokens=100)
        assert "chunk one" in ctx
        assert "chunk two" in ctx

    def test_assemble_respects_token_limit(self):
        """Context assembly stops at token limit."""
        assembler = ContextAssembler()
        chunks = [
            {"text": " ".join(["word"] * 100)},
            {"text": " ".join(["extra"] * 100)},
        ]
        ctx = assembler.assemble("query", chunks, max_tokens=50)
        assert len(ctx.split()) <= 50

    def test_assemble_empty_chunks(self):
        """Empty chunks produce empty context."""
        assembler = ContextAssembler()
        ctx = assembler.assemble("query", [], max_tokens=100)
        assert ctx == ""

    def test_assemble_preserves_order(self):
        """Chunks appear in the order provided."""
        assembler = ContextAssembler()
        chunks = [
            {"text": "first chunk"},
            {"text": "second chunk"},
        ]
        ctx = assembler.assemble("query", chunks, max_tokens=100)
        assert ctx.index("first") < ctx.index("second")
