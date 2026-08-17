from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .ports.cognitive_service import VersionedCognitiveService
from .ports.context_provider import ContextProvider
from .ports.embedding_provider import EmbeddingProvider
from .ports.model_service import ModelService
from .ports.projection import ProjectionAdapter, ProjectionReceipt
from .ports.reranker import Reranker
from .ports.retriever import Retriever
from .ports.verification_service import VerificationService
