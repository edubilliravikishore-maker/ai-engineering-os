"""The OS Kernel — the only layer that mutates, audits, and publishes.

Blueprint 2.2 places ``core`` above ``rules``, ``state``, ``storage`` and
``events``, and it is the only package that imports all four. That is
deliberate: the components beneath it each answer one question and none of them
may write anything, so something has to compose them, and composing them in
exactly one place is what makes the Validation-First invariant of Blueprint 7.2
verifiable rather than hoped for.

- :mod:`~ai_engineering_os.core.context_loader` reads facts and hands them over.
- :mod:`~ai_engineering_os.core.routing` decides who reviews a submitted Task.
- :mod:`~ai_engineering_os.core.runner` owns the transaction and the ordering.
- :mod:`~ai_engineering_os.core.kernel` exposes the operations.
"""

from ai_engineering_os.core.context_loader import load_rule_context
from ai_engineering_os.core.kernel import OSKernel
from ai_engineering_os.core.routing import eligible_reviewers, select_reviewer
from ai_engineering_os.core.runner import (
    TransitionRequest,
    TransitionResult,
    TransitionRunner,
)

__all__ = [
    "OSKernel",
    "TransitionRequest",
    "TransitionResult",
    "TransitionRunner",
    "eligible_reviewers",
    "load_rule_context",
    "select_reviewer",
]
