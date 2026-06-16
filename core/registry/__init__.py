from core.registry.dependencies import require_module, require_module_dep
from core.registry.schemas import (
    ModuleFlag,
    ModuleMetadata,
    ModuleRegistryResponse,
    ModuleStatus,
    ModuleToggleRequest,
)
from core.registry.service import ModuleRegistryService, module_registry_service

__all__ = [
    "ModuleFlag",
    "ModuleMetadata",
    "ModuleRegistryResponse",
    "ModuleRegistryService",
    "ModuleStatus",
    "ModuleToggleRequest",
    "module_registry_service",
    "require_module",
    "require_module_dep",
]
