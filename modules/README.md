# Modules

Service modules for the BlueHub platform. Each module provides a specific product type.

## Current Modules

- **vpn/** - VPN services (WireGuard, VLESS+REALITY)
- **vps/** - Virtual Private Server management (Proxmox)
- **smartdns/** - Smart DNS services
- **streaming/** - Streaming service accounts
- **game/** - Game service accounts

## Module Structure

Each module follows this structure:
- `models.py` - SQLAlchemy database models
- `schemas.py` - Pydantic request/response schemas
- `services.py` - Business logic
- `metadata.py` - Module metadata for auto-discovery
- `__init__.py` - Module registration