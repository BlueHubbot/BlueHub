"""
Game Module Metadata
====================
Module definition for Game hosting services (game servers, voice servers).
"""

from core.registry.schemas import ModuleFlag, ModuleMetadata

metadata = ModuleMetadata(
    name="game",
    display_name="Game Service",
    description="Game server hosting services including Minecraft, Valheim, and voice server hosting",
    version="1.0.0",
    order=50,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="sports_esports",
    tags=["gaming", "hosting", "voice"],
)

__all__ = ["metadata"]
