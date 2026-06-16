from typing import Any

import pytest

# Simple Mock DB representing multi-tenant configurations
mock_tenant_db: dict[str, dict[str, Any]] = {
    "tenant-alpha": {
        "name": "Reseller Alpha",
        "active": True,
        "branding": {"primary_color": "#4CAF50"}
    },
    "tenant-beta": {
        "name": "White-Label Beta",
        "active": False,
        "branding": {"primary_color": "#FF9800"}
    }
}

class TenantContextResolver:
    """
    Core helper that checks structural validity of tenant status.
    Enforces logical isolation boundaries for multi-tenant requests.
    """
    @staticmethod
    def resolve(tenant_id: str) -> dict[str, Any]:
        if not tenant_id:
            msg = "X-Tenant-Id header cannot be null or empty"
            raise ValueError(msg)

        tenant = mock_tenant_db.get(tenant_id)
        if not tenant:
            msg = f"Tenant with ID {tenant_id} is not registered"
            raise LookupError(msg)

        if not tenant["active"]:
            msg = f"Tenant with ID {tenant_id} is suspended"
            raise PermissionError(msg)

        return tenant

# ----------------------------------------------------------------------
# UNIT TESTS (FastAPI Async Compatible)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_tenant_success():
    """Verifies the context resolver properly handles a valid, active tenant."""
    tenant_data = TenantContextResolver.resolve("tenant-alpha")
    assert tenant_data["name"] == "Reseller Alpha"
    assert tenant_data["active"] is True

@pytest.mark.asyncio
async def test_resolve_tenant_empty():
    """Ensures that passing an empty string as a tenant ID raises a ValueError."""
    with pytest.raises(ValueError, match="X-Tenant-Id header cannot be null"):
        TenantContextResolver.resolve("")

@pytest.mark.asyncio
async def test_resolve_tenant_missing():
    """Ensures that querying an unregistered tenant raises a LookupError."""
    with pytest.raises(LookupError, match="not registered"):
        TenantContextResolver.resolve("tenant-unknown")

@pytest.mark.asyncio
async def test_resolve_tenant_suspended():
    """Ensures that querying a suspended tenant raises a PermissionError."""
    with pytest.raises(PermissionError, match="is suspended"):
        TenantContextResolver.resolve("tenant-beta")
