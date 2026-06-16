"""
SmartDNS Module Metadata
========================
Module definition for SmartDNS services.
"""

from core.registry.schemas import ModuleFlag, ModuleMetadata

metadata = ModuleMetadata(
    name="smartdns",
    display_name="SmartDNS Service",
    description="Smart DNS proxy services for bypassing geo-restrictions and DNS-based content filtering",
    version="1.0.0",
    order=30,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="smart_dns",
    tags=["dns", "proxy", "geo-unblock"],
)

__all__ = ["metadata"]
