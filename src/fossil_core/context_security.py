from __future__ import annotations

import copy
import hashlib
from typing import Any, Iterable, Mapping

from .application.query.security import (
    CONTEXT_SECURITY_RESOLVER,
    UNTRUSTED_SOURCE_DATA,
    UntrustedContextModelService,
    canonicalize_untrusted_context,
)
