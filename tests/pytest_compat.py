"""
pytest compatibility module for environments without pytest installed.
Provides pytest.raises, pytest.mark, pytest.fixture, etc. using unittest.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self


class _RaisesContext:
    """Context manager similar to pytest.raises."""

    def __init__(self, expected_exception: type[BaseException], match: str | None = None):
        self.expected_exception = expected_exception
        self.match = match
        self.exception: BaseException | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None,
                 exc_tb: Any | None) -> bool:
        if exc_type is None:
            msg = f"DID NOT RAISE {self.expected_exception.__name__}"
            raise AssertionError(
                msg
            )
        if not issubclass(exc_type, self.expected_exception):
            return False
        self.exception = exc_val
        if self.match is not None:
            import re
            if not re.search(self.match, str(exc_val or "")):
                msg = f"Exception pattern '{self.match}' not found in '{exc_val}'"
                raise AssertionError(
                    msg
                )
        return True


class _Mark:
    """Mock for pytest.mark."""

    def __getattr__(self, name: str) -> Any:
        return _MarkerDecorator(name)


class _MarkerDecorator:
    """Mock for pytest.mark.xfail, pytest.mark.skip, etc."""

    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            return func
        return decorator


class _Fixture:
    """Mock for pytest.fixture."""

    def __call__(self, func: Callable) -> Callable:
        return func

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        pass


mark = _Mark()
fixture = _Fixture()


def raises(expected_exception: type[BaseException], match: str | None = None) -> _RaisesContext:
    """Similar to pytest.raises."""
    return _RaisesContext(expected_exception, match)


def skip(reason: str = "") -> Callable:
    """Similar to pytest.skip."""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


def skipif(condition: bool, reason: str = "") -> Callable:
    """Similar to pytest.skipif."""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


def xfail(reason: str = "") -> Callable:
    """Similar to pytest.xfail."""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


def param(*values: Any, id: str | None = None, marks: Any = None) -> Any:
    """Similar to pytest.param."""
    return values


class _Approx:
    """Similar to pytest.approx."""
    def __init__(self, expected: Any, rel: float | None = None, abs: float | None = None):
        self.expected = expected


def approx(expected: Any, rel: float | None = None, abs: float | None = None) -> _Approx:
    """Similar to pytest.approx."""
    return _Approx(expected, rel, abs)


__all__ = ["approx", "fixture", "mark", "param", "raises", "skip", "skipif", "xfail"]
