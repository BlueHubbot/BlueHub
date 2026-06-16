"""
pytest compatibility shim - provides pytest API without real pytest.
Works when pytest is not installed.
"""
# Also provide asyncio mark support
import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

from tests.pytest_compat import *  # noqa: F403

T = TypeVar("T")


def _run_async(coro):
    """Run an async test function."""
    return asyncio.run(coro)


class _AsyncMark:
    """Marks a test function as async."""

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_async(func(*args, **kwargs))
        return wrapper


# Override mark.asyncio
from tests.pytest_compat import mark

mark.asyncio = _AsyncMark()
