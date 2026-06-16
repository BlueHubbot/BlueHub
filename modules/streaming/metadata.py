"""
Streaming Module Metadata
=========================
Module definition for Streaming services (IPTV, media servers).
"""

from core.registry.schemas import ModuleFlag, ModuleMetadata

metadata = ModuleMetadata(
    name="streaming",
    display_name="Streaming Service",
    description="IPTV and media streaming services including live TV, VOD, and catch-up content",
    version="1.0.0",
    order=40,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="streaming",
    tags=["media", "iptv", "vod", "entertainment"],
)

__all__ = ["metadata"]
