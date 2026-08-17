"""Narrow LiteLLM cognitive-service adapters."""

from .embedding import (
    GEMINI_EMBEDDING_2_ACCEPTED_ACTUAL_MODELS,
    GEMINI_EMBEDDING_2_CANONICAL_MODEL,
    GEMINI_EMBEDDING_2_DIMENSION,
    GEMINI_EMBEDDING_2_REQUESTED_MODEL,
    GeminiEmbedding2IdentityError,
    GeminiEmbedding2ProtocolError,
    GeminiEmbedding2Provider,
    GeminiEmbedding2TransportError,
)
from .reranker import (
    LiteLLMReranker,
    LiteLLMRerankerIdentityError,
    LiteLLMRerankerProtocolError,
    LiteLLMRerankerTransportError,
)

__all__ = [
    "GEMINI_EMBEDDING_2_ACCEPTED_ACTUAL_MODELS",
    "GEMINI_EMBEDDING_2_CANONICAL_MODEL",
    "GEMINI_EMBEDDING_2_DIMENSION",
    "GEMINI_EMBEDDING_2_REQUESTED_MODEL",
    "GeminiEmbedding2IdentityError",
    "GeminiEmbedding2ProtocolError",
    "GeminiEmbedding2Provider",
    "GeminiEmbedding2TransportError",
    "LiteLLMReranker",
    "LiteLLMRerankerIdentityError",
    "LiteLLMRerankerProtocolError",
    "LiteLLMRerankerTransportError",
]
