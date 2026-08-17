from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from .application.ingest import KnowledgePackValidator
from .domain.pack import PackAccess, PackBoundaryError
