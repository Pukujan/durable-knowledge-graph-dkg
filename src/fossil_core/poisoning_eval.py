from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .answer_eval import build_answer_context
from .application.evaluation.answer import AnswerReliabilityCase, evaluate_answer_candidate
from .application.query.poisoning_eval import (
    RetrievalPoisoningCase,
    run_retrieval_poisoning_benchmark,
)
