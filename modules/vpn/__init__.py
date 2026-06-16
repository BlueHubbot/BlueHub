"""
VPN Module Package
==================
Provides VPN protocol implementations including WireGuard and Xray-core (VLESS+REALITY).
"""

from modules.vpn.xray import (
    # Constants
    DEFAULT_ALPN,
    DEFAULT_FALLBACK_SNI,
    DEFAULT_FINGERPRINT,
    DEFAULT_FLOW,
    DEFAULT_NETWORK,
    DEFAULT_SECURITY,
    DEFAULT_SHORT_ID_LENGTH,
    DEFAULT_SNI_DOMAIN,
    DEFAULT_VLESS_PORT,
    DEFAULT_XRAY_API_PORT,
    DEFAULT_XRAY_API_TAG,
    DEFAULT_XRAY_CONFIG_DIR,
    DEFAULT_XRAY_EXECUTABLE,
    # Data Classes
    RealityConfig,
    RealityKeyPair,
    XrayInboundInfo,
    XrayServerConfig,
    XrayTraffic,
    # Main Service Class
    XrayService,
    # Exceptions
    XrayAPIConnectionError,
    XrayCommandError,
    XrayConfigError,
    XrayError,
    XrayKeyGenerationError,
)

__all__: list[str] = [
    # Xray imports
    "DEFAULT_ALPN",
    "DEFAULT_FALLBACK_SNI",
    "DEFAULT_FINGERPRINT",
    "DEFAULT_FLOW",
    "DEFAULT_NETWORK",
    "DEFAULT_SECURITY",
    "DEFAULT_SHORT_ID_LENGTH",
    "DEFAULT_SNI_DOMAIN",
    "DEFAULT_VLESS_PORT",
    "DEFAULT_XRAY_API_PORT",
    "DEFAULT_XRAY_API_TAG",
    "DEFAULT_XRAY_CONFIG_DIR",
    "DEFAULT_XRAY_EXECUTABLE",
    "RealityConfig",
    "RealityKeyPair",
    "XrayInboundInfo",
    "XrayServerConfig",
    "XrayTraffic",
    "XrayService",
    "XrayAPIConnectionError",
    "XrayCommandError",
    "XrayConfigError",
    "XrayError",
    "XrayKeyGenerationError",
]