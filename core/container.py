"""
BlueHub Dependency Injection Container
========================================
Central IoC container using dependency-injector.
Manages all application services and their dependencies.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from core.config import Settings


class CoreContainer(containers.DeclarativeContainer):
    """
    Core IoC container holding foundational application services.
    This container provides config, database, cache, and other core services.
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "core.database",
            "core.cache",
            "core.repositories.base",
            "core.repositories.unit_of_work",
        ]
    )

    # --- Configuration ---
    config: providers.Singleton[Settings] = providers.Singleton(
        Settings.get_settings
    )

    # --- Database ---
    # These will be configured when database module is imported
    db_session_factory = providers.Singleton(lambda: None)
    db_session = providers.ThreadLocalSingleton(lambda: None)

    # --- Redis Cache ---
    redis_client = providers.Singleton(lambda: None)
    cache_service = providers.Singleton(lambda: None)

    # --- Logging ---
    logger = providers.Singleton(lambda: None)


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Top-level application container.
    Assembles all modules and their dependencies.
    """

    core: providers.Container[CoreContainer] = providers.Container(
        CoreContainer
    )

    # Module containers will be wired here in later phases
    # vpn = providers.Container(VPNContainer)
    # vps = providers.Container(VPSContainer)
    # smartdns = providers.Container(SmartDNSContainer)
    # streaming = providers.Container(StreamingContainer)
    # game = providers.Container(GameContainer)

    # API and Bot containers
    # api = providers.Container(APIContainer)
    # bot = providers.Container(BotContainer)


# Global application container instance
app_container = ApplicationContainer()

__all__ = [
    "ApplicationContainer",
    "CoreContainer",
    "app_container",
]
