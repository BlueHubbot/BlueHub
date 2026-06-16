"""
BlueHub Shared Core Base
===========================
Re-exports base model classes from core and adds shared model mixins.
"""

from core.models.base import Base, IDMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin

__all__ = [
    "CoreBase",
    "IDMixin",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
]


class CoreBase(Base):
    """
    Core base class for all BlueHub models.
    Inherits from the main Base with UUID primary keys by default.
    """

    __abstract__ = True
