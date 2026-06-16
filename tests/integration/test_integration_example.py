from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

# ----------------------------------------------------------------------
# MOCK APPLICATION FOR MULTI-TENANT HANDSHAKE VERIFICATION
# ----------------------------------------------------------------------
app = FastAPI()

async def verify_tenant_routing_header(x_tenant_id: str = Header(None)) -> str:
    """
    Tenant extraction and isolation validation.
    Matches requirements defined in .clinerules.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header is missing")
    if x_tenant_id == "suspended-tenant":
        raise HTTPException(status_code=403, detail="Tenant status is suspended")
    return x_tenant_id

@app.get("/v1/modules")
async def list_modules(tenant_id: str = Depends(verify_tenant_routing_header)) -> dict[str, Any]:
    """
    Simulated product/module lookup.
    Returns tenant-specific module status configurations.
    """
    return {
        "tenant_id": tenant_id,
        "modules": [
            {"name": "vpn", "enabled": True},
            {"name": "vps", "enabled": False}
        ]
    }

client = TestClient(app)

# ----------------------------------------------------------------------
# INTEGRATION TESTS
# ----------------------------------------------------------------------

def test_api_resolves_valid_tenant_header():
    """
    Verifies that the API correctly parses X-Tenant-Id and processes request
    complying with core isolation requirements.
    """
    response = client.get("/v1/modules", headers={"X-Tenant-Id": "partner-delta"})
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "partner-delta"
    assert data["modules"][0]["name"] == "vpn"
    assert data["modules"][0]["enabled"] is True

def test_api_rejects_missing_tenant_header():
    """
    Verifies that requests missing the mandatory X-Tenant-Id header
    are rejected with a 400 Bad Request error.
    """
    response = client.get("/v1/modules")
    assert response.status_code == 400
    assert "X-Tenant-Id" in response.json()["detail"]

def test_api_rejects_suspended_tenant():
    """
    Verifies that a suspended tenant header triggers a 403 Forbidden
    error immediately.
    """
    response = client.get("/v1/modules", headers={"X-Tenant-Id": "suspended-tenant"})
    assert response.status_code == 403
    assert "suspended" in response.json()["detail"]
