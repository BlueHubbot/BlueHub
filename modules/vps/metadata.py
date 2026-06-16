"""
VPS Module Metadata
===================
Module definition for VPS services (virtual private servers).
"""

from core.registry.schemas import ModuleFlag, ModuleMetadata

metadata = ModuleMetadata(
    name="vps",
    display_name="VPS Service",
    description="Virtual Private Server services with KVM-based virtualization and SSD storage",
    version="1.0.0",
    order=20,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="dns",
    tags=["compute", "virtualization", "cloud"],
)

__all__ = ["metadata"]
