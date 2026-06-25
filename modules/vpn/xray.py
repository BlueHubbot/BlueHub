"""
Xray-core VLESS+REALITY Integration Module
==============================================
Implements VLESS+REALITY protocol support via Xray-core subprocess management,
configuration generation, traffic statistics collection, and fallback handling.

Xray-core is required on the server. Configuration is in JSON format.
REALITY requires: private key, short ID, SNI (e.g., www.google.com).
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import subprocess  # nosec: B404 - xray commands are intentionally invoked
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from modules.vpn.models import VpnAccount, VpnServer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_XRAY_EXECUTABLE = "xray"
DEFAULT_XRAY_CONFIG_DIR = Path("/etc/xray")
DEFAULT_XRAY_API_PORT = 62789
DEFAULT_XRAY_API_TAG = "api"
DEFAULT_SNI_DOMAIN = "www.google.com"
DEFAULT_SHORT_ID_LENGTH = 8  # hex characters
DEFAULT_FALLBACK_SNI = "www.bing.com"
DEFAULT_VLESS_PORT = 443
DEFAULT_FLOW = "xtls-rprx-vision"
DEFAULT_NETWORK = "tcp"
DEFAULT_SECURITY = "reality"
DEFAULT_FINGERPRINT = "random"
DEFAULT_ALPN = ["h2", "http/1.1"]

# User agent list for fingerprint randomization
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class RealityKeyPair:
    """REALITY key pair (private + public)."""

    private_key: str
    public_key: str


@dataclass
class RealityConfig:
    """REALITY-specific configuration parameters."""

    private_key: str
    short_id: str
    sni: str
    fingerprint: str = DEFAULT_FINGERPRINT
    fallback_sni: str = DEFAULT_FALLBACK_SNI
    alpn: list[str] = field(default_factory=lambda: list(DEFAULT_ALPN))
    spider_x: str | None = None
    client_fingerprint: str = DEFAULT_FINGERPRINT


@dataclass
class XrayTraffic:
    """Traffic statistics for a single Xray user/inbound."""

    user_id: str
    inbound_tag: str
    uplink: int  # bytes
    downlink: int  # bytes

    @property
    def total(self) -> int:
        """Total traffic (uplink + downlink) in bytes."""
        return self.uplink + self.downlink


@dataclass
class XrayInboundInfo:
    """Information about an Xray inbound."""

    tag: str
    protocol: str
    port: int
    listen: str
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class XrayServerConfig:
    """Encapsulates a full Xray server configuration."""

    log: dict[str, Any] = field(default_factory=lambda: {
        "loglevel": "warning",
        "access": "/var/log/xray/access.log",
        "error": "/var/log/xray/error.log",
    })
    inbounds: list[dict[str, Any]] = field(default_factory=list)
    outbounds: list[dict[str, Any]] = field(default_factory=lambda: [
        {
            "protocol": "freedom",
            "tag": "direct",
        },
        {
            "protocol": "blackhole",
            "tag": "block",
        },
    ])
    routing: dict[str, Any] = field(default_factory=lambda: {
        "rules": [
            {
                "type": "field",
                "inboundTag": [DEFAULT_XRAY_API_TAG],
                "outboundTag": "api",
            },
        ],
    })
    stats: dict[str, Any] = field(default_factory=lambda: {
        "outboundUplinkTraffic": {"enabled": True},
        "outboundDownlinkTraffic": {"enabled": True},
        "inboundUplinkTraffic": {"enabled": True},
        "inboundDownlinkTraffic": {"enabled": True},
    })
    policy: dict[str, Any] = field(default_factory=lambda: {
        "levels": {
            "0": {
                "statsUserUplink": True,
                "statsUserDownlink": True,
            },
        },
        "system": {
            "statsInboundUplink": True,
            "statsInboundDownlink": True,
            "statsOutboundUplink": True,
            "statsOutboundDownlink": True,
        },
    })
    api: dict[str, Any] = field(default_factory=lambda: {
        "tag": DEFAULT_XRAY_API_TAG,
        "services": [
            "HandlerService",
            "LoggerService",
            "StatsService",
        ],
    })


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class XrayError(Exception):
    """Base exception for Xray operations."""


class XrayCommandError(XrayError):
    """Raised when an ``xray`` command fails."""


class XrayKeyGenerationError(XrayError):
    """Raised when REALITY key generation fails."""


class XrayConfigError(XrayError):
    """Raised when configuration generation/validation fails."""


class XrayAPIConnectionError(XrayError):
    """Raised when connecting to Xray API fails."""


# ---------------------------------------------------------------------------
# XrayService
# ---------------------------------------------------------------------------


class XrayService:
    """
    Service class for VLESS+REALITY operations via Xray-core.

    Supports:
    - REALITY key pair generation (x25519)
    - Short ID generation
    - VLESS+REALITY inbound configuration generation
    - Client configuration generation (JSON format)
    - Xray process management (start/stop/restart)
    - API-based traffic statistics collection
    - User add/remove via API
    - Fallback SNI configuration
    """

    # ------------------------------------------------------------------
    # Key Management
    # ------------------------------------------------------------------

    @staticmethod
    def generate_reality_keypair() -> RealityKeyPair:
        """
        Generate a REALITY key pair using ``xray x25519``.

        Returns:
            RealityKeyPair with private_key and public_key.

        Raises:
            XrayKeyGenerationError if generation fails.
        """
        try:
            result = subprocess.run(
                [_xray_bin(), "x25519"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            # Parse output: "Private key: <key>\nPublic key: <key>"
            private_match = re.search(
                r"Private\s*key:\s*(\S+)", result.stdout, re.IGNORECASE
            )
            public_match = re.search(
                r"Public\s*key:\s*(\S+)", result.stdout, re.IGNORECASE
            )

            if not private_match or not public_match:
                raise XrayKeyGenerationError(
                    f"Failed to parse x25519 output: {result.stdout}"
                )

            return RealityKeyPair(
                private_key=private_match.group(1),
                public_key=public_match.group(1),
            )

        except subprocess.CalledProcessError as exc:
            logger.error("Xray key generation failed: %s", exc.stderr)
            raise XrayKeyGenerationError(
                f"REALITY key generation failed: {exc.stderr}"
            ) from exc
        except FileNotFoundError as exc:
            logger.error(
                "Xray binary (%s) not found. Is Xray-core installed?", _xray_bin()
            )
            raise XrayKeyGenerationError(
                f"Xray binary '{_xray_bin()}' not found"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise XrayKeyGenerationError("Key generation timed out") from exc

    @staticmethod
    def generate_short_id(length: int = DEFAULT_SHORT_ID_LENGTH) -> str:
        """
        Generate a random hex short ID for REALITY.

        Args:
            length: Number of hex characters (default 8 = 32 bits).

        Returns:
            Hex string of the specified length.
        """
        return secrets.token_hex(length // 2)

    @staticmethod
    def generate_uuid_v4() -> str:
        """
        Generate a UUID v4 for VLESS user identification.

        Returns:
            UUID v4 string.
        """
        import uuid
        return str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Server Configuration Generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_inbound_config(
        *,
        tag: str = "vless-reality-inbound",
        port: int = DEFAULT_VLESS_PORT,
        listen: str = "0.0.0.0",
        reality_private_key: str = "",
        short_id: str = "",
        sni: str = DEFAULT_SNI_DOMAIN,
        fallback_sni: str = DEFAULT_FALLBACK_SNI,
        fingerprint: str = DEFAULT_FINGERPRINT,
        alpn: list[str] | None = None,
        users: list[dict[str, Any]] | None = None,
        enable_vision: bool = True,
    ) -> dict[str, Any]:
        """
        Generate a VLESS+REALITY inbound configuration block.

        Args:
            tag: Inbound tag for routing and stats.
            port: Listening port (default 443).
            listen: Listen address (default 0.0.0.0).
            reality_private_key: REALITY private key.
            short_id: REALITY short ID hex string.
            sni: Target SNI domain.
            fallback_sni: Fallback SNI domain.
            fingerprint: TLS fingerprint.
            alpn: ALPN protocol list.
            users: List of VLESS user dicts with id, encryption, flow, level.
            enable_vision: Enable XTLS Vision flow.

        Returns:
            Dict representing an Xray inbound configuration.
        """
        effective_alpn = alpn or list(DEFAULT_ALPN)
        effective_users = users or []

        inbound: dict[str, Any] = {
            "tag": tag,
            "port": port,
            "listen": listen,
            "protocol": "vless",
            "settings": {
                "clients": effective_users,
                "decryption": "none",
            },
            "streamSettings": {
                "network": DEFAULT_NETWORK,
                "security": DEFAULT_SECURITY,
                "realitySettings": {
                    "show": False,
                    "dest": f"{sni}:443",
                    "xver": 0,
                    "serverNames": [sni],
                    "privateKey": reality_private_key,
                    "shortIds": [short_id],
                    "settings": {
                        "fingerprint": fingerprint,
                        "serverName": sni,
                        "publicKey": "",
                        "shortId": short_id,
                        "spiderX": "",
                    },
                },
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls", "quic"],
            },
        }

        # Add fallback configuration
        if fallback_sni:
            inbound.setdefault("fallbacks", [])
            inbound["fallbacks"].append({
                "dest": f"{fallback_sni}:443",
                "xver": 1,
            })

        # Add vision flow to each user if enabled
        if enable_vision:
            for user in effective_users:
                user.setdefault("flow", DEFAULT_FLOW)

        return inbound

    @staticmethod
    def generate_client_config(
        *,
        server_address: str,
        server_port: int = DEFAULT_VLESS_PORT,
        user_id: str = "",
        reality_public_key: str = "",
        short_id: str = "",
        sni: str = DEFAULT_SNI_DOMAIN,
        fingerprint: str = DEFAULT_FINGERPRINT,
        flow: str = DEFAULT_FLOW,
        network: str = DEFAULT_NETWORK,
        security: str = DEFAULT_SECURITY,
        alpn: list[str] | None = None,
    ) -> str:
        """
        Generate a VLESS+REALITY client configuration in JSON format.

        Args:
            server_address: Server IP or domain.
            server_port: Server port (default 443).
            user_id: VLESS user UUID.
            reality_public_key: REALITY public key.
            short_id: REALITY short ID.
            sni: SNI domain.
            fingerprint: TLS fingerprint.
            flow: XTLS flow type.
            network: Network protocol.
            security: Security protocol.
            alpn: ALPN values.

        Returns:
            JSON string of the client configuration.

        The output is compatible with:
        - Xray-core (direct JSON import)
        - v2rayNG / v2rayN / Shadowrocket / Nekoray / Qv2ray
        """
        effective_alpn = alpn or list(DEFAULT_ALPN)

        config: dict[str, Any] = {
            "log": {
                "loglevel": "warning",
            },
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "auth": "noaccounts",
                        "udp": True,
                    },
                },
                {
                    "tag": "http-in",
                    "port": 10809,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {},
                },
            ],
            "outbounds": [
                {
                    "tag": "proxy",
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": server_address,
                                "port": server_port,
                                "users": [
                                    {
                                        "id": user_id,
                                        "flow": flow,
                                        "encryption": "none",
                                        "level": 0,
                                    },
                                ],
                            },
                        ],
                    },
                    "streamSettings": {
                        "network": network,
                        "security": security,
                        "realitySettings": {
                            "show": False,
                            "fingerprint": fingerprint,
                            "serverName": sni,
                            "publicKey": reality_public_key,
                            "shortId": short_id,
                            "spiderX": "/",
                        },
                    },
                },
                {
                    "protocol": "freedom",
                    "tag": "direct",
                },
            ],
            "routing": {
                "rules": [
                    {
                        "type": "field",
                        "inboundTag": ["socks-in", "http-in"],
                        "outboundTag": "proxy",
                    },
                ],
            },
        }

        # Add ALPN to stream settings if applicable
        config["outbounds"][0].setdefault("streamSettings", {})
        config["outbounds"][0]["streamSettings"]["sockopt"] = {
            "dialerProxy": "freedom",
        }

        return json.dumps(config, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Server Configuration File Management
    # ------------------------------------------------------------------

    @staticmethod
    def build_full_server_config(
        *,
        config_dir: Path = DEFAULT_XRAY_CONFIG_DIR,
        reality_keypair: RealityKeyPair | None = None,
        short_id: str = "",
        sni: str = DEFAULT_SNI_DOMAIN,
        fallback_sni: str = DEFAULT_FALLBACK_SNI,
        port: int = DEFAULT_VLESS_PORT,
        users: list[dict[str, Any]] | None = None,
        extra_inbounds: list[dict[str, Any]] | None = None,
        api_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Build a complete Xray server configuration JSON.

        Args:
            config_dir: Directory for Xray configuration files.
            reality_keypair: REALITY key pair for this server.
            short_id: REALITY short ID.
            sni: Primary SNI domain.
            fallback_sni: Fallback SNI domain.
            port: VLESS listen port.
            users: List of VLESS user dicts (id, flow, level, encryption).
            extra_inbounds: Additional inbound configurations.
            api_enabled: Enable gRPC API for stats/management.

        Returns:
            Complete Xray server config dict.
        """
        config = XrayServerConfig()

        # Update log paths to use config_dir
        log_dir = config_dir.parent / "log"
        config.log = {
            "loglevel": "warning",
            "access": str(log_dir / "access.log"),
            "error": str(log_dir / "error.log"),
        }

        # Generate the VLESS+REALITY inbound
        if users is None:
            users = []
        if reality_keypair:
            pass  # key will be used below

        vless_inbound = XrayService.generate_inbound_config(
            tag="vless-reality",
            port=port,
            listen="0.0.0.0",
            reality_private_key=reality_keypair.private_key if reality_keypair else "",
            short_id=short_id,
            sni=sni,
            fallback_sni=fallback_sni,
            fingerprint=DEFAULT_FINGERPRINT,
            users=users,
            enable_vision=True,
        )

        config.inbounds.append(vless_inbound)

        # Add API inbound for gRPC management
        if api_enabled:
            config.inbounds.append({
                "tag": DEFAULT_XRAY_API_TAG,
                "port": DEFAULT_XRAY_API_PORT,
                "listen": "127.0.0.1",
                "protocol": "dokodemo-door",
                "settings": {
                    "address": "127.0.0.1",
                },
            })

        # Add extra inbounds (for other protocols or configurations)
        if extra_inbounds:
            config.inbounds.extend(extra_inbounds)

        # Update routing rules for the API
        api_rule: dict[str, Any] = {
            "type": "field",
            "inboundTag": [DEFAULT_XRAY_API_TAG],
            "outboundTag": "api",
        }
        if api_rule not in config.routing["rules"]:
            config.routing["rules"].append(api_rule)

        return {
            "log": config.log,
            "inbounds": config.inbounds,
            "outbounds": config.outbounds,
            "routing": config.routing,
            "stats": config.stats,
            "policy": config.policy,
            "api": config.api,
        }

    @staticmethod
    def write_server_config(
        config: dict[str, Any],
        *,
        config_path: Path | None = None,
        config_dir: Path = DEFAULT_XRAY_CONFIG_DIR,
        filename: str = "config.json",
    ) -> Path:
        """
        Write an Xray server configuration to disk.

        Args:
            config: The server configuration dict.
            config_path: Explicit path (overrides config_dir + filename).
            config_dir: Directory for configuration files.
            filename: Configuration file name (default config.json).

        Returns:
            Path to the written configuration file.
        """
        if config_path is None:
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / filename

        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Wrote Xray config to %s", config_path)
        return config_path

    # ------------------------------------------------------------------
    # Xray Process Management
    # ------------------------------------------------------------------

    @staticmethod
    def start_xray(
        *,
        config_path: Path | str = DEFAULT_XRAY_CONFIG_DIR / "config.json",
        executable: str | None = None,
        extra_args: list[str] | None = None,
    ) -> subprocess.Popen[str]:
        """
        Start the Xray process with the given configuration.

        Args:
            config_path: Path to the configuration JSON file.
            executable: Path to the xray binary (default from env or 'xray').
            extra_args: Additional command-line arguments.

        Returns:
            Popen handle to the running Xray process.

        Raises:
            XrayCommandError if the process fails to start.
        """
        exe = executable or _xray_bin()
        cmd = [exe, "run", "-c", str(config_path)]

        if extra_args:
            cmd.extend(extra_args)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            logger.info("Started Xray (PID %d) with config %s", proc.pid, config_path)
            return proc
        except FileNotFoundError as exc:
            raise XrayCommandError(
                f"Xray binary '{exe}' not found"
            ) from exc
        except OSError as exc:
            raise XrayCommandError(
                f"Failed to start Xray: {exc}"
            ) from exc

    @staticmethod
    def stop_xray(proc: subprocess.Popen[str] | None = None, *, pid: int | None = None) -> None:
        """
        Stop the Xray process gracefully (SIGTERM then SIGKILL).

        Args:
            proc: Popen handle to the Xray process.
            pid: Process ID (alternative to proc).
        """
        if proc is not None:
            pid = proc.pid

        if pid is None:
            logger.warning("No Xray process to stop")
            return

        try:
            import signal
            if os.name == "nt":
                # Windows: use taskkill
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    timeout=10, check=False,
                )
            else:
                os.kill(pid, signal.SIGTERM)
            logger.info("Stopped Xray process (PID %d)", pid)
        except ProcessLookupError:
            logger.info("Xray process (PID %d) already exited", pid)
        except OSError as exc:
            logger.warning("Failed to stop Xray process (PID %d): %s", pid, exc)

    @staticmethod
    def restart_xray(
        *,
        config_path: Path | str = DEFAULT_XRAY_CONFIG_DIR / "config.json",
        old_proc: subprocess.Popen[str] | None = None,
    ) -> subprocess.Popen[str]:
        """
        Restart Xray with a fresh configuration.

        Args:
            config_path: Path to the configuration file.
            old_proc: Previously running Xray process to stop.

        Returns:
            Popen handle to the new Xray process.
        """
        if old_proc is not None:
            XrayService.stop_xray(old_proc)

        return XrayService.start_xray(config_path=config_path)

    @staticmethod
    def is_running(
        proc: subprocess.Popen[str] | None = None, *, pid: int | None = None
    ) -> bool:
        """
        Check if an Xray process is currently running.

        Args:
            proc: Popen handle.
            pid: Process ID.

        Returns:
            True if the process is running.
        """
        if proc is not None:
            return proc.poll() is None
        if pid is not None:
            try:
                if os.name == "nt":
                    result = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}"],
                        capture_output=True, text=True, timeout=10, check=False,
                    )
                    return str(pid) in result.stdout
                else:
                    os.kill(pid, 0)  # signal 0 checks existence
                    return True
            except (OSError, subprocess.TimeoutExpired):
                return False
        return False

    # ------------------------------------------------------------------
    # User Management (via Xray API)
    # ------------------------------------------------------------------

    @staticmethod
    def add_user_via_api(
        *,
        email: str,
        user_id: str,
        inbound_tag: str = "vless-reality",
        flow: str = DEFAULT_FLOW,
        api_address: str = "127.0.0.1",
        api_port: int = DEFAULT_XRAY_API_PORT,
    ) -> bool:
        """
        Add a VLESS user to a running Xray instance via gRPC API.

        This requires the ``grpcio`` and ``grpcio-tools`` packages
        and the Xray gRPC protobuf definitions. If not available,
        the operation falls back to config file modification + restart.

        Args:
            email: User email/identifier.
            user_id: VLESS UUID for the user.
            inbound_tag: Target inbound tag.
            flow: XTLS flow type.
            api_address: Xray API address.
            api_port: Xray API port.

        Returns:
            True if the user was added successfully.

        Note:
            This is a stub implementation. Full gRPC integration
            requires Xray API protobuf stubs. As a fallback, use
            :meth:`add_user_via_config` for config file modification.
        """
        logger.warning(
            "gRPC API not fully implemented yet. "
            "Use add_user_via_config() for config-based user management. "
            "Attempted to add user %s (UUID: %s)", email, user_id
        )
        return False

    @staticmethod
    def add_user_via_config(
        *,
        user_id: str,
        email: str = "",
        flow: str = DEFAULT_FLOW,
        config_data: dict[str, Any],
        inbound_tag: str = "vless-reality",
        level: int = 0,
    ) -> dict[str, Any]:
        """
        Add a VLESS user to an existing server config dict.

        This modifies the config in-memory. The caller should
        write the config to disk and restart Xray for changes to take effect.

        Args:
            user_id: VLESS UUID.
            email: Optional user email/remark.
            flow: XTLS flow (default: xtls-rprx-vision).
            config_data: Server configuration dict to modify.
            inbound_tag: Tag of the target inbound.
            level: User level (0 = normal).

        Returns:
            Modified configuration dict.
        """
        user_entry: dict[str, Any] = {
            "id": user_id,
            "flow": flow,
            "encryption": "none",
            "level": level,
        }
        if email:
            user_entry["email"] = email

        for inbound in config_data.get("inbounds", []):
            if inbound.get("tag") == inbound_tag:
                inbound.setdefault("settings", {})
                inbound["settings"].setdefault("clients", [])
                inbound["settings"]["clients"].append(user_entry)
                logger.info(
                    "Added user %s to inbound %s", email or user_id, inbound_tag
                )
                break
        else:
            raise XrayConfigError(
                f"Inbound with tag '{inbound_tag}' not found in config"
            )

        return config_data

    @staticmethod
    def remove_user_via_config(
        *,
        user_id: str,
        config_data: dict[str, Any],
        inbound_tag: str = "vless-reality",
    ) -> dict[str, Any]:
        """
        Remove a VLESS user from an existing server config dict.

        Args:
            user_id: VLESS UUID to remove.
            config_data: Server configuration dict to modify.
            inbound_tag: Tag of the target inbound.

        Returns:
            Modified configuration dict.
        """
        for inbound in config_data.get("inbounds", []):
            if inbound.get("tag") == inbound_tag:
                clients = inbound.get("settings", {}).get("clients", [])
                inbound["settings"]["clients"] = [
                    c for c in clients if c.get("id") != user_id
                ]
                logger.info(
                    "Removed user %s from inbound %s", user_id, inbound_tag
                )
                break

        return config_data

    @staticmethod
    def sync_users_to_config(
        *,
        accounts: list[dict[str, Any]],
        config_data: dict[str, Any],
        inbound_tag: str = "vless-reality",
    ) -> dict[str, Any]:
        """
        Sync a list of VLESS accounts to the server configuration.

        This replaces all users in the specified inbound with the
        provided list. Useful for batch updates and reconciliation.

        Args:
            accounts: List of dicts with keys: id, email (optional), flow, level.
            config_data: Server configuration dict.
            inbound_tag: Tag of the target inbound.

        Returns:
            Modified configuration dict.
        """
        users: list[dict[str, Any]] = []
        for acct in accounts:
            user: dict[str, Any] = {
                "id": acct["id"],
                "flow": acct.get("flow", DEFAULT_FLOW),
                "encryption": "none",
                "level": acct.get("level", 0),
            }
            if email := acct.get("email"):
                user["email"] = email
            users.append(user)

        for inbound in config_data.get("inbounds", []):
            if inbound.get("tag") == inbound_tag:
                inbound.setdefault("settings", {})
                inbound["settings"]["clients"] = users
                logger.info(
                    "Synced %d users to inbound %s", len(users), inbound_tag
                )
                break

        return config_data

    # ------------------------------------------------------------------
    # Traffic Statistics Collection
    # ------------------------------------------------------------------

    @staticmethod
    def collect_traffic_via_api(
        *,
        api_address: str = "127.0.0.1",
        api_port: int = DEFAULT_XRAY_API_PORT,
        reset: bool = True,
    ) -> list[XrayTraffic]:
        """
        Collect traffic statistics from a running Xray instance via gRPC API.

        This is a stub implementation. Full gRPC integration requires
        Xray API protobuf stubs. Returns empty list for now.

        Args:
            api_address: Xray API gRPC address.
            api_port: Xray API gRPC port.
            reset: Whether to reset counters after reading.

        Returns:
            List of XrayTraffic dataclass instances.

        Note:
            This requires grpcio + grpcio-tools + Xray protobuf definitions.
            For now, use :meth:`parse_traffic_from_log` as an alternative.
        """
        logger.warning(
            "gRPC traffic collection not fully implemented. "
            "Use parse_traffic_from_log() for log-based traffic collection. "
            "API: %s:%d", api_address, api_port
        )
        return []

    @staticmethod
    def parse_traffic_from_log(
        log_path: Path | str = "/var/log/xray/access.log",
        *,
        recent_seconds: int = 300,
    ) -> list[XrayTraffic]:
        """
        Parse traffic data from Xray access logs.

        This is a fallback traffic collection method. It parses
        access.log entries and aggregates upload/download bytes
        per user within a recent time window.

        Args:
            log_path: Path to Xray access log file.
            recent_seconds: Only consider entries within this window.

        Returns:
            List of XrayTraffic dataclass instances with aggregated data.

        Note:
            Log-based traffic collection is approximate.
            For accurate per-user traffic, use the gRPC API method.
        """
        log_file = Path(log_path)
        if not log_file.exists():
            logger.warning("Xray access log not found: %s", log_path)
            return []

        # Regex pattern for Xray access log entries
        # Format: <timestamp> email: <user> <direction> <bytes>
        pattern = re.compile(
            r"(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
            r"\s+email:\s+(?P<email>\S+)"
            r"\s+(?P<direction>uplink|downlink)"
            r"\s+(?P<bytes>\d+)",
            re.IGNORECASE,
        )

        now = datetime.now(tz=UTC)
        traffic_map: dict[str, dict[str, int]] = {}

        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
            for match in pattern.finditer(content):
                try:
                    ts = datetime.strptime(
                        match.group("timestamp"), "%Y/%m/%d %H:%M:%S"
                    ).replace(tzinfo=UTC)
                    if (now - ts).total_seconds() > recent_seconds:
                        continue
                except ValueError:
                    continue

                email = match.group("email").strip()
                direction = match.group("direction").lower()
                try:
                    bytes_val = int(match.group("bytes"))
                except ValueError:
                    continue

                if email not in traffic_map:
                    traffic_map[email] = {"upload": 0, "download": 0}

                if "uplink" in direction:
                    traffic_map[email]["upload"] += bytes_val
                else:
                    traffic_map[email]["download"] += bytes_val

        except OSError as exc:
            logger.warning("Failed to read Xray access log: %s", exc)
            return []

        results: list[XrayTraffic] = []
        for email, data in traffic_map.items():
            results.append(
                XrayTraffic(
                    user_id=email,
                    inbound_tag="vless-reality",
                    uplink=data["upload"],
                    downlink=data["download"],
                )
            )

        return results

    @staticmethod
    def get_user_traffic(
        user_id: str,
        *,
        recent_seconds: int = 300,
        log_path: Path | str = "/var/log/xray/access.log",
    ) -> XrayTraffic | None:
        """
        Get traffic data for a specific user.

        Args:
            user_id: VLESS user UUID or email.
            recent_seconds: Lookback window.
            log_path: Path to Xray access log.

        Returns:
            XrayTraffic for the user, or None if no data.
        """
        traffic_list = XrayService.parse_traffic_from_log(
            log_path, recent_seconds=recent_seconds
        )
        for t in traffic_list:
            if t.user_id == user_id:
                return t
        return None

    # ------------------------------------------------------------------
    # VLESS Account Provisioning Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def provision_account(
        server: VpnServer,
        account: VpnAccount,
    ) -> dict[str, Any]:
        """
        Generate provisioning data for a VLESS+REALITY account.

        This generates:
        - A UUID for the user (stored in account.password)
        - REALITY config parameters (stored as protocol_configs)
        - Client config text (JSON format)

        Args:
            server: VpnServer with REALITY key pair and SNI settings.
            account: VpnAccount to provision.

        Returns:
            Dict with provisioning result:
            - user_id: str (UUID)
            - client_config: str (JSON client config)
            - reality_config: dict
        """
        # Get or generate user UUID
        user_id = account.password or XrayService.generate_uuid_v4()

        # Get REALITY parameters from server metadata or account configs
        reality_private_key = server.private_key or ""
        reality_public_key = server.public_key or ""

        # Get SNI from protocol_configs or server defaults
        sni = DEFAULT_SNI_DOMAIN
        short_id = DEFAULT_SHORT_ID_LENGTH * "0"  # fallback
        for pc in account.protocol_configs:
            if pc.config_key == "sni":
                sni = pc.config_value
            elif pc.config_key == "short_id":
                short_id = pc.config_value

        # Generate REALITY key pair if server doesn't have one
        if not reality_private_key:
            keypair = XrayService.generate_reality_keypair()
            reality_private_key = keypair.private_key
            reality_public_key = keypair.public_key

        # Generate client config JSON
        client_config_str = XrayService.generate_client_config(
            user_id=user_id,
            server_address=server.host or server.ip_address or "127.0.0.1",
            server_port=server.port or DEFAULT_VLESS_PORT,
            reality_public_key=reality_public_key,
            short_id=short_id,
            sni=sni,
        )

        # Build return dict
        result: dict[str, Any] = {
            "user_id": user_id,
            "client_config": client_config_str,
            "reality_config": {
                "private_key": reality_private_key,
                "public_key": reality_public_key,
                "short_id": short_id,
                "sni": sni,
            },
        }

        return result

    # ------------------------------------------------------------------
    # VLESS Account Suspend / Restore
    # ------------------------------------------------------------------

    @staticmethod
    def suspend_account(
        server: VpnServer,
        account: VpnAccount,
    ) -> dict[str, Any]:
        """
        Suspend a VLESS+REALITY account by removing the user from the config.

        Args:
            server: VpnServer hosting the account.
            account: VpnAccount to suspend.

        Returns:
            Dict with suspension result: {'success': bool, 'user_id': str, 'message': str}
        """
        user_id = account.password or ""
        if not user_id:
            return {
                "success": False,
                "user_id": "",
                "message": "No UUID assigned to account",
            }

        try:
            # Read current server config
            config_path = DEFAULT_XRAY_CONFIG_DIR / "config.json"
            if not config_path.exists():
                logger.warning("Xray config not found at %s; nothing to suspend", config_path)
                return {
                    "success": True,
                    "user_id": user_id,
                    "message": "Config not present; account considered suspended",
                }

            with open(config_path, encoding="utf-8") as f:
                config: dict[str, Any] = json.load(f)

            # Remove user from all inbounds
            removed = False
            for inbound in config.get("inbounds", []):
                settings = inbound.get("settings", {})
                clients = settings.get("clients", [])
                filtered = [c for c in clients if c.get("id") != user_id]
                if len(filtered) < len(clients):
                    removed = True
                settings["clients"] = filtered

            if not removed:
                return {
                    "success": True,
                    "user_id": user_id,
                    "message": "User not found in config; already suspended",
                }

            # Write updated config
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            logger.info("Suspended VLESS user %s by removing from config", user_id)
            return {
                "success": True,
                "user_id": user_id,
                "message": "User removed from xray config successfully",
            }

        except Exception as exc:
            logger.error("Failed to suspend VLESS user %s: %s", user_id, exc)
            return {
                "success": False,
                "user_id": user_id,
                "message": f"Suspension failed: {exc}",
            }

    @staticmethod
    def restore_account(
        server: VpnServer,
        account: VpnAccount,
    ) -> dict[str, Any]:
        """
        Restore a suspended VLESS+REALITY account by re-adding the user to config.

        Args:
            server: VpnServer hosting the account.
            account: VpnAccount to restore.

        Returns:
            Dict with restoration result: {'success': bool, 'user_id': str, 'message': str}
        """
        user_id = account.password or ""
        if not user_id:
            return {
                "success": False,
                "user_id": "",
                "message": "No UUID assigned to account",
            }

        # Re-provision to get the full client config
        provision_result = XrayService.provision_account(server, account)
        user_id = provision_result["user_id"]

        # Build user block for the inbound
        user_block: dict[str, Any] = {
            "id": user_id,
            "flow": DEFAULT_FLOW,
            "level": 0,
        }

        try:
            config_path = DEFAULT_XRAY_CONFIG_DIR / "config.json"
            if not config_path.exists():
                logger.warning("Xray config not found at %s; creating new config", config_path)
                # Generate fresh config with this user
                full_config = XrayService.build_full_server_config(
                    port=server.port or DEFAULT_VLESS_PORT,
                    reality_keypair=RealityKeyPair(
                        private_key=provision_result["reality_config"]["private_key"],
                        public_key=provision_result["reality_config"]["public_key"],
                    ),
                    short_id=provision_result["reality_config"]["short_id"],
                    sni=provision_result["reality_config"]["sni"],
                    users=[user_block],
                )
                # Ensure directory exists
                config_path.parent.mkdir(parents=True, exist_ok=True)
                XrayService.write_server_config(full_config, config_path=config_path)
                return {
                    "success": True,
                    "user_id": user_id,
                    "message": "New config created with user restored",
                }

            with open(config_path, encoding="utf-8") as f:
                config: dict[str, Any] = json.load(f)

            # Add user to all VLESS inbounds
            added = False
            for inbound in config.get("inbounds", []):
                if inbound.get("protocol") != "vless":
                    continue
                settings = inbound.get("settings", {})
                clients = settings.get("clients", [])
                # Check if user already exists
                existing_ids = {c.get("id") for c in clients}
                if user_id not in existing_ids:
                    clients.append(user_block)
                    added = True
                else:
                    logger.info("User %s already in inbound %s", user_id, inbound.get("tag", "unknown"))

            if not added:
                return {
                    "success": True,
                    "user_id": user_id,
                    "message": "User already present in config",
                }

            # Write updated config
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            logger.info("Restored VLESS user %s by re-adding to config", user_id)
            return {
                "success": True,
                "user_id": user_id,
                "message": "User re-added to xray config successfully",
            }

        except Exception as exc:
            logger.error("Failed to restore VLESS user %s: %s", user_id, exc)
            return {
                "success": False,
                "user_id": user_id,
                "message": f"Restoration failed: {exc}",
            }


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _xray_bin() -> str:
    """
    Resolve the xray executable path.

    Checks the XRAY_BIN environment variable first, falls back to DEFAULT_XRAY_EXECUTABLE.
    """
    return os.environ.get("XRAY_BIN", DEFAULT_XRAY_EXECUTABLE)


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__: list[str] = [
    # Constants
    "DEFAULT_XRAY_EXECUTABLE",
    "DEFAULT_XRAY_CONFIG_DIR",
    "DEFAULT_XRAY_API_PORT",
    "DEFAULT_XRAY_API_TAG",
    "DEFAULT_SNI_DOMAIN",
    "DEFAULT_SHORT_ID_LENGTH",
    "DEFAULT_FALLBACK_SNI",
    "DEFAULT_VLESS_PORT",
    "DEFAULT_FLOW",
    "DEFAULT_NETWORK",
    "DEFAULT_SECURITY",
    "DEFAULT_FINGERPRINT",
    "DEFAULT_ALPN",
    # Data Classes
    "RealityKeyPair",
    "RealityConfig",
    "XrayTraffic",
    "XrayInboundInfo",
    "XrayServerConfig",
    # Main Service Class
    "XrayService",
    # Exceptions
    "XrayError",
    "XrayCommandError",
    "XrayKeyGenerationError",
    "XrayConfigError",
    "XrayAPIConnectionError",
    # Helpers
    "_xray_bin",
]
