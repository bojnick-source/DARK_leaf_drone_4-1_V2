"""Deprecation helpers for managing API lifecycle.

Provides a lightweight decorator and warning utility for marking
functions, classes, or parameters as deprecated with guidance on
replacements.
"""

from __future__ import annotations

import functools
import warnings
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def deprecated(reason: str, *, removal_version: str | None = None) -> Callable[[F], F]:
    """Decorator to mark a function or method as deprecated.

    Args:
        reason: Explanation of what to use instead.
        removal_version: Optional version string when the function will be removed.
    """

    def decorator(func: F) -> F:
        removal_note = (
            f" Scheduled for removal in {removal_version}."
            if removal_version is not None
            else ""
        )
        message = f"{func.__qualname__} is deprecated: {reason}{removal_note}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
