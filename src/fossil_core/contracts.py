from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .ports import (
    ContextProvider,
    EmbeddingProvider,
    ModelService,
    ProjectionAdapter,
    ProjectionReceipt,
    Reranker,
    Retriever,
    VerificationService,
    VersionedCognitiveService,
)
