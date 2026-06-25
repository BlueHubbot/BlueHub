"""
BlueHub Module Registry Service
================================
Service for scanning, registering, and managing module feature flags.
Supports Redis caching with 60-second TTL for enabled state lookups.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.registry.schemas import (
    ModuleFlag,
    ModuleMetadata,
    ModuleRegistryResponse,
    ModuleToggleRequest,
)
from shared.models.module_registry import ModuleRegistry

logger = logging.getLogger(__name__)

# Redis cache keys
_MODULE_ENABLED_PREFIX = "module:enabled:"
_MODULE_FLAGS_PREFIX = "module:flags:"
_CACHE_TTL = 60  # seconds


class ModuleRegistryService:
    """
    Service for module registry management.

    Handles scanning module metadata files, registering modules in the
    database, checking enabled state with Redis caching, and toggling
    feature flags.
    """

    def __init__(self) -> None:
        self._redis = None  # Lazy-loaded redis client
        self._modules_base: str | None = None

    # ── Redis Helpers ────────────────────────────────────────────────────

    async def _get_redis(self) -> Any:
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                from core.config import settings

                self._redis = aioredis.from_url(
                    str(settings.REDIS_URL),
                    decode_responses=True,
                )
            except Exception:
                logger.warning("Redis unavailable, falling back to DB-only mode")
                self._redis = None  # type: ignore[assignment]
        return self._redis

    # ── Module Discovery ─────────────────────────────────────────────────

    def _discover_metadata_modules(self) -> dict[str, ModuleMetadata]:
        """
        Scan modules/*/metadata.py files and import their metadata.

        Returns:
            Dictionary mapping module name -> ModuleMetadata
        """
        modules_dir = self._get_modules_base()
        discovered: dict[str, ModuleMetadata] = {}

        if not os.path.isdir(modules_dir):
            logger.warning("Modules directory not found: %s", modules_dir)
            return discovered

        for entry in sorted(os.listdir(modules_dir)):
            metadata_path = os.path.join(modules_dir, entry, "metadata.py")
            if not os.path.isfile(metadata_path):
                continue

            module_name = self._import_metadata(modules_dir, entry)
            if module_name:
                discovered[module_name] = module_name  # type: ignore[assignment]

        return discovered

    def _get_modules_base(self) -> str:
        """Get the absolute path to the modules directory."""
        if self._modules_base is None:
            # Determine project root - one level up from core/registry
            core_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(core_dir))
            self._modules_base = os.path.join(project_root, "modules")
        return self._modules_base

    def _import_metadata(self, modules_dir: str, module_entry: str) -> str | None:
        """
        Import metadata from a module's metadata.py file.

        Args:
            modules_dir: Absolute path to the modules directory.
            module_entry: Directory name of the module (e.g., 'vpn').

        Returns:
            ModuleMetadata instance or None if import failed.
        """
        module_path = f"modules.{module_entry}.metadata"
        try:
            import importlib

            mod = importlib.import_module(module_path)
            metadata: ModuleMetadata = getattr(mod, "metadata", None)
            if metadata is None:
                logger.warning(
                    "Module %s has no 'metadata' attribute, skipping",
                    module_entry,
                )
                return None
            if not isinstance(metadata, ModuleMetadata):
                logger.warning(
                    "Module %s metadata is not a ModuleMetadata instance, skipping",
                    module_entry,
                )
                return None
            return metadata
        except Exception:
            logger.exception(
                "Failed to import metadata for module %s",
                module_entry,
            )
            return None

    async def scan_modules(self) -> dict[str, ModuleMetadata]:
        """
        Scan the modules directory for all metadata files.

        Returns:
            Dictionary mapping module name to ModuleMetadata.
        """
        modules = self._discover_metadata_modules()
        # Re-import properly to get actual ModuleMetadata objects
        core_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(core_dir))
        modules_dir = os.path.join(project_root, "modules")
        discovered: dict[str, ModuleMetadata] = {}

        for entry in sorted(os.listdir(modules_dir)):
            metadata_path = os.path.join(modules_dir, entry, "metadata.py")
            if not os.path.isfile(metadata_path):
                continue
            try:
                import importlib

                mod = importlib.import_module(f"modules.{entry}.metadata")
                meta: ModuleMetadata = getattr(mod, "metadata", None)
                if isinstance(meta, ModuleMetadata):
                    discovered[meta.name] = meta
            except Exception:
                logger.exception("Failed to scan module: %s", entry)

        return discovered

    # ── Database Registration ────────────────────────────────────────────

    async def register_modules(self, session: AsyncSession) -> int:
        """
        Scan and register all discovered modules in the database.

        Creates new records for modules not yet registered, and updates
        existing records with fresh metadata.

        Args:
            session: An active database session.

        Returns:
            Number of modules registered or updated.
        """
        modules = await self.scan_modules()
        count = 0

        for module_name, meta in modules.items():
            # Check if module already exists
            result = await session.execute(
                select(ModuleRegistry).where(
                    ModuleRegistry.module_name == module_name
                )
            )
            existing = result.scalar_one_or_none()

            flag_dict = (
                {
                    "enabled": meta.default_flags.enabled,
                    "stop_new_sales": meta.default_flags.stop_new_sales,
                    "terminate_services": meta.default_flags.terminate_services,
                    "maintenance_mode": meta.default_flags.maintenance_mode,
                }
                if meta.default_flags
                else {}
            )

            # Serialize optional nested configs
            bot_keyboard_dict = (
                meta.bot_keyboard.model_dump() if meta.bot_keyboard else None
            )
            admin_menu_dict = (
                meta.admin_menu.model_dump() if meta.admin_menu else None
            )

            if existing:
                # Update existing record
                existing.display_name = meta.display_name
                existing.description = meta.description or ""
                existing.version = meta.version
                existing.order = meta.order
                existing.config_schema = meta.config_schema
                existing.flags = flag_dict
                existing.bot_keyboard = bot_keyboard_dict
                existing.admin_menu = admin_menu_dict
                existing.default_config = meta.default_config
                logger.info("Updated module registration: %s", module_name)
            else:
                # Create new record
                entry = ModuleRegistry(
                    module_name=module_name,
                    display_name=meta.display_name,
                    description=meta.description or "",
                    version=meta.version,
                    enabled=meta.default_flags.enabled if meta.default_flags else True,
                    order=meta.order,
                    config_schema=meta.config_schema,
                    flags=flag_dict,
                    bot_keyboard=bot_keyboard_dict,
                    admin_menu=admin_menu_dict,
                    default_config=meta.default_config,
                )
                session.add(entry)
                logger.info("Registered new module: %s", module_name)

            count += 1

        await session.commit()
        logger.info("Registered/updated %d modules", count)
        return count

    # ── Module State Queries ─────────────────────────────────────────────

    async def is_module_enabled(
        self,
        module_name: str,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        Check if a module is enabled, with Redis cache (60s TTL).

        Args:
            module_name: The module identifier (e.g., 'vpn').
            session: Optional database session for fallback lookup.

        Returns:
            True if the module is enabled, False otherwise.
        """
        # Try Redis cache first
        redis = await self._get_redis()
        if redis:
            try:
                cached = await redis.get(f"{_MODULE_ENABLED_PREFIX}{module_name}")
                if cached is not None:
                    return cached == "1"
            except Exception:
                logger.debug("Redis lookup failed for %s", module_name)

        # Fallback to database
        if session is not None:
            result = await session.execute(
                select(ModuleRegistry.enabled).where(
                    ModuleRegistry.module_name == module_name
                )
            )
            enabled = result.scalar_one_or_none()
            if enabled is not None:
                # Cache the result
                if redis:
                    try:
                        await redis.setex(
                            f"{_MODULE_ENABLED_PREFIX}{module_name}",
                            _CACHE_TTL,
                            "1" if enabled else "0",
                        )
                    except Exception:
                        pass
                return enabled

        # Default to True if not found
        logger.warning("Module %s not found in registry, defaulting to enabled", module_name)
        return True

    async def get_module_flags(
        self,
        module_name: str,
        session: AsyncSession,
    ) -> ModuleFlag:
        """
        Get feature flags for a module.

        Args:
            module_name: The module identifier.
            session: Active database session.

        Returns:
            ModuleFlag with the current state.
        """
        # Try Redis cache first
        redis = await self._get_redis()
        if redis:
            try:
                cached = await redis.get(f"{_MODULE_FLAGS_PREFIX}{module_name}")
                if cached is not None:
                    import json

                    data = json.loads(cached)
                    return ModuleFlag(**data)
            except Exception:
                pass

        # Fallback to database
        result = await session.execute(
            select(ModuleRegistry).where(
                ModuleRegistry.module_name == module_name
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return ModuleFlag()

        flags = entry.flags or {}
        flag = ModuleFlag(
            enabled=flags.get("enabled", True),
            stop_new_sales=flags.get("stop_new_sales", False),
            terminate_services=flags.get("terminate_services", False),
            maintenance_mode=flags.get("maintenance_mode", False),
        )

        # Cache the flags
        if redis:
            try:
                import json

                await redis.setex(
                    f"{_MODULE_FLAGS_PREFIX}{module_name}",
                    _CACHE_TTL,
                    flag.model_dump_json(),
                )
            except Exception:
                pass

        return flag

    async def get_all_modules(
        self,
        session: AsyncSession,
    ) -> Sequence[ModuleRegistry]:
        """
        Get all registered modules.

        Args:
            session: Active database session.

        Returns:
            List of ModuleRegistry entries.
        """
        result = await session.execute(
            select(ModuleRegistry).order_by(ModuleRegistry.order)
        )
        return result.scalars().all()

    async def toggle_module(
        self,
        module_name: str,
        request: ModuleToggleRequest,
        session: AsyncSession,
    ) -> ModuleRegistryResponse | None:
        """
        Toggle module feature flags.

        Args:
            module_name: The module identifier.
            request: The toggle request with fields to update.
            session: Active database session.

        Returns:
            Updated ModuleRegistryResponse or None if module not found.
        """
        result = await session.execute(
            select(ModuleRegistry).where(
                ModuleRegistry.module_name == module_name
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return None

        # Update flags
        current_flags = entry.flags or {}
        if request.enabled is not None:
            entry.enabled = request.enabled
            current_flags["enabled"] = request.enabled
        if request.stop_new_sales is not None:
            current_flags["stop_new_sales"] = request.stop_new_sales
        if request.terminate_services is not None:
            current_flags["terminate_services"] = request.terminate_services
        if request.maintenance_mode is not None:
            current_flags["maintenance_mode"] = request.maintenance_mode

        entry.flags = current_flags
        await session.commit()
        await session.refresh(entry)

        # Invalidate cache
        redis = await self._get_redis()
        if redis:
            try:
                await redis.delete(
                    f"{_MODULE_ENABLED_PREFIX}{module_name}",
                    f"{_MODULE_FLAGS_PREFIX}{module_name}",
                )
            except Exception:
                pass

        return self._to_response(entry)

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _to_response(entry: ModuleRegistry) -> ModuleRegistryResponse:
        """Convert a ModuleRegistry ORM entry to a response schema."""
        flags = entry.flags or {}
        return ModuleRegistryResponse(
            id=str(entry.id) if entry.id else None,
            module_name=entry.module_name,
            display_name=entry.display_name,
            description=entry.description,
            version=entry.version,
            enabled=entry.enabled,
            order=entry.order or 0,
            flags=ModuleFlag(
                enabled=flags.get("enabled", True),
                stop_new_sales=flags.get("stop_new_sales", False),
                terminate_services=flags.get("terminate_services", False),
                maintenance_mode=flags.get("maintenance_mode", False),
            ),
        )


# Singleton instance
module_registry_service = ModuleRegistryService()


__all__ = [
    "ModuleRegistryService",
    "module_registry_service",
]
