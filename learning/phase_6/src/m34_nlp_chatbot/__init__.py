"""
M34: NLP & Chatbot — Intent classification, named entity recognition, and RAG.

This module builds the natural language understanding pipeline for a
ride-sharing chatbot: classifying what users want (intent), extracting
structured data from messages (NER), and retrieving relevant knowledge
to generate accurate responses (RAG).
"""

from .intent_classifier import IntentType, KeywordMatcher, TFIDFClassifier, MultiIntentDetector
from .named_entity import EntityType, Entity, RegexNER, RuleBasedNER, EntityLinker
from .rag_retriever import Document, DocumentChunker, TFIDFRetriever, BM25Reranker, ContextAssembler
