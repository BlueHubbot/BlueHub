"""
WireGuard VPN Integration Module
===================================
Implements WireGuard key generation, client configuration, QR code generation,
server-side peer management, traffic polling, and suspension/restoration.

Uses ``subprocess`` to call ``wg`` commands for local server management.
For remote servers, an SSH tunnel or management API is expected.
"""

from __future__ import annotations

import base64
import io
import logging
import re
import subprocess  # nosec: B404 - wg commands are intentionally invoked
from dataclasses import dataclass
from datetime import timezone, datetime
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import qrcode  # type: ignore[import-untyped]
except ImportError:
    qrcode = None

if TYPE_CHECKING:
    from modules.vpn.models import VpnAccount, VpnServer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WG_INTERFACE = "wg0"
DEFAULT_CONFIG_DIR = Path("/etc/wireguard")
DEFAULT_DNS_SERVERS = "1.1.1.1, 8.8.8.8"
DEFAULT_ALLOWED_IPS = "0.0.0.0/0, ::/0"
DEFAULT_KEEPALIVE = 25  # seconds
DEFAULT_MTU = 1420
WG_EXECUTABLE = "wg"  # path to the wg command; override via environment if needed

# Regex patterns for parsing wg show output
_WG_PEER_BLOCK = re.compile(
    r"^peer:\s+(?P<public_key>[A-Za-z0-9+/=]{44})\s*\n"
    r"(?:.*\n)*?"
    r"(?=^peer:|^$)",
    re.MULTILINE,
)
_WG_FIELD = re.compile(r"^\s+(?P<key>[\w\s]+):\s+(?P<value>.+)$", re.MULTILINE)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class WireGuardKeyPair:
    """WireGuard key pair (private + public)."""

    private_key: str
    public_key: str


@dataclass
class PeerTraffic:
    """Traffic and status data for a single WireGuard peer."""

    public_key: str
    transfer_rx: int  # bytes received
    transfer_tx: int  # bytes sent
    last_handshake: datetime | None
    endpoint: str | None
    allowed_ips: str | None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WireGuardError(Exception):
    """Base exception for WireGuard operations."""


class WireGuardCommandError(WireGuardError):
    """Raised when a ``wg`` command fails."""


class WireGuardKeyGenerationError(WireGuardError):
    """Raised when key generation fails."""


# ---------------------------------------------------------------------------
# WireGuardService
# ---------------------------------------------------------------------------


class WireGuardService:
    """
    Service class for all WireGuard VPN operations.

    Supports:
    - Key pair generation
    - Preshared key generation
    - Client configuration file generation
    - QR code generation
    - Local server peer add / remove / restore
    - Traffic polling via ``wg show``
    - Connection / disconnection status detection
    """

    # ------------------------------------------------------------------
    # Key Management
    # ------------------------------------------------------------------

    @staticmethod
    def generate_keypair() -> WireGuardKeyPair:
        """
        Generate a WireGuard key pair.

        Returns:
            WireGuardKeyPair with private_key and public_key.

        Raises:
            WireGuardKeyGenerationError if generation fails.
        """
        try:
            # Generate private key
            priv_result = subprocess.run(
                [_wg_bin(), "genkey"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            private_key = priv_result.stdout.strip()

            # Derive public key from private key
            pub_result = subprocess.run(
                [_wg_bin(), "pubkey"],
                input=private_key,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            public_key = pub_result.stdout.strip()

            return WireGuardKeyPair(private_key=private_key, public_key=public_key)

        except subprocess.CalledProcessError as exc:
            logger.error("WireGuard key generation failed: %s", exc.stderr)
            raise WireGuardKeyGenerationError(
                f"Key generation failed: {exc.stderr}"
            ) from exc
        except FileNotFoundError as exc:
            logger.error(
                "WireGuard binary (%s) not found. Is WireGuard installed?", _wg_bin()
            )
            raise WireGuardKeyGenerationError(
                f"WireGuard binary '{_wg_bin()}' not found"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise WireGuardKeyGenerationError("Key generation timed out") from exc

    @staticmethod
    def generate_preshared_key() -> str:
        """
        Generate a WireGuard preshared key.

        Returns:
            Base64-encoded preshared key string.
        """
        try:
            result = subprocess.run(
                [_wg_bin(), "genpsk"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            logger.error("Preshared key generation failed: %s", exc.stderr)
            raise WireGuardKeyGenerationError(
                f"Preshared key generation failed: {exc.stderr}"
            ) from exc
        except FileNotFoundError as exc:
            raise WireGuardKeyGenerationError(
                f"WireGuard binary '{_wg_bin()}' not found"
            ) from exc

    # ------------------------------------------------------------------
    # Client Configuration Generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_client_config(
        server: VpnServer,
        account: VpnAccount,
        *,
        dns: str = DEFAULT_DNS_SERVERS,
        mtu: int = DEFAULT_MTU,
        persistent_keepalive: int = DEFAULT_KEEPALIVE,
    ) -> str:
        """
        Generate a wg-quick compatible client configuration file.

        Args:
            server: VpnServer instance with public_key, endpoint, port.
            account: VpnAccount instance with private_key, preshared_key,
                     allowed_ips, dns_servers, assigned_ip.
            dns: DNS servers override.
            mtu: MTU value.
            persistent_keepalive: PersistentKeepalive seconds.

        Returns:
            INI-style WireGuard client config as a string.
        """
        lines: list[str] = [
            "[Interface]",
            f"PrivateKey = {account.private_key or ''}",
            f"Address = {account.assigned_ip or '10.0.0.2/32'}",
        ]

        # Custom DNS (use account-level if set, otherwise default)
        effective_dns = account.dns_servers or dns
        lines.append(f"DNS = {effective_dns}")

        if mtu:
            lines.append(f"MTU = {mtu}")

        lines.append("")
        lines.append("[Peer]")
        lines.append(f"PublicKey = {server.public_key or ''}")

        if account.preshared_key:
            lines.append(f"PresharedKey = {account.preshared_key}")

        lines.append(f"Endpoint = {server.endpoint}")

        effective_allowed_ips = account.allowed_ips or DEFAULT_ALLOWED_IPS
        lines.append(f"AllowedIPs = {effective_allowed_ips}")

        if persistent_keepalive:
            lines.append(f"PersistentKeepalive = {persistent_keepalive}")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # QR Code Generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_qr_code(config_text: str) -> str:
        """
        Generate a QR code PNG image as a base64-encoded string.

        Args:
            config_text: The WireGuard client config text.

        Returns:
            Base64-encoded PNG image string (suitable for embedding in HTML/JSON).
        """
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(config_text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("ascii")

    # ------------------------------------------------------------------
    # Server-Side Peer Management (Local) – via ``wg set``
    # ------------------------------------------------------------------

    @staticmethod
    def add_peer_to_server(
        server: VpnServer,
        account: VpnAccount,
        *,
        interface: str = DEFAULT_WG_INTERFACE,
    ) -> None:
        """
        Add a client peer to a local WireGuard interface.

        Uses ``wg set <interface> peer <pubkey> ...``

        Args:
            server: VpnServer instance.
            account: VpnAccount with public_key, preshared_key, assigned_ip, allowed_ips.
            interface: WireGuard interface name (default wg0).

        Raises:
            WireGuardCommandError on failure.
        """
        if not account.public_key:
            raise WireGuardError("Cannot add peer without a public key")

        cmd = [
            _wg_bin(),
            "set",
            interface,
            "peer",
            account.public_key,
        ]

        if account.preshared_key:
            cmd.extend(["--preshared-key", account.preshared_key])

        allowed_ips = account.allowed_ips or account.assigned_ip or "10.0.0.2/32"
        cmd.extend(["--allowed-ips", allowed_ips])

        _run_wg_command(cmd)

        logger.info(
            "Added peer %s to interface %s on server %s",
            account.public_key[:16],
            interface,
            server.name,
        )

    @staticmethod
    def remove_peer_from_server(
        server: VpnServer,
        account: VpnAccount,
        *,
        interface: str = DEFAULT_WG_INTERFACE,
    ) -> None:
        """
        Remove a client peer from a local WireGuard interface (suspension).

        Uses ``wg set <interface> peer <pubkey> remove``

        Args:
            server: VpnServer instance.
            account: VpnAccount with public_key.
            interface: WireGuard interface name.

        Raises:
            WireGuardCommandError on failure.
        """
        if not account.public_key:
            raise WireGuardError("Cannot remove peer without a public key")

        cmd = [
            _wg_bin(),
            "set",
            interface,
            "peer",
            account.public_key,
            "remove",
        ]

        _run_wg_command(cmd)

        logger.info(
            "Removed peer %s from interface %s on server %s",
            account.public_key[:16],
            interface,
            server.name,
        )

    @staticmethod
    def restore_peer(
        server: VpnServer,
        account: VpnAccount,
        *,
        interface: str = DEFAULT_WG_INTERFACE,
    ) -> None:
        """
        Re-add a previously removed peer (service restoration).

        This is equivalent to :meth:`add_peer_to_server` but intended for
        restoration after a suspension.

        Args:
            server: VpnServer instance.
            account: VpnAccount with public_key, preshared_key, assigned_ip.
            interface: WireGuard interface name.
        """
        WireGuardService.add_peer_to_server(server, account, interface=interface)

    # ------------------------------------------------------------------
    # Server-Side Config Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_config(
        *,
        interface: str = DEFAULT_WG_INTERFACE,
        config_dir: Path = DEFAULT_CONFIG_DIR,
    ) -> None:
        """
        Persist the current runtime configuration to the config file.

        Wraps ``wg-quick save <interface>`` or equivalent.

        Args:
            interface: WireGuard interface name.
            config_dir: Path to the WireGuard configuration directory.
        """
        config_path = config_dir / f"{interface}.conf"
        try:
            result = subprocess.run(
                [_wg_bin(), "showconf", interface],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            config_path.write_text(result.stdout)
            logger.info("Saved WireGuard config for interface %s", interface)
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Failed to save WireGuard config: %s", exc.stderr
            )
        except OSError as exc:
            logger.warning("Cannot write config file %s: %s", config_path, exc)

    # ------------------------------------------------------------------
    # Traffic Polling
    # ------------------------------------------------------------------

    @staticmethod
    def poll_traffic(
        *,
        interface: str = DEFAULT_WG_INTERFACE,
    ) -> list[PeerTraffic]:
        """
        Poll traffic and status data from a WireGuard interface.

        Parses the output of ``wg show <interface> dump``.

        Args:
            interface: WireGuard interface name.

        Returns:
            List of PeerTraffic dataclass instances.
        """
        try:
            result = subprocess.run(
                [_wg_bin(), "show", interface, "dump"],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning(
                "Failed to poll WireGuard traffic on %s: %s", interface, exc
            )
            return []

        peers: list[PeerTraffic] = []
        # wg show dump output format (tab-separated):
        #   private_key  port  fwmark
        #   public_key  preshared_key  endpoint  allowed_ips  latest_handshake  rx_bytes  tx_bytes  persistent_keepalive
        lines = result.stdout.strip().split("\n")
        for line in lines[1:]:  # skip first line (interface info)
            parts = line.split("\t")
            if len(parts) < 7:
                continue

            public_key = parts[0]
            # parts[1] = preshared_key (ignored here)
            endpoint = parts[2] or None
            # parts[3] = allowed_ips (ignored here, we get the raw data)
            allowed_ips_raw = parts[3]
            try:
                last_handshake_ts = int(parts[4])
                last_handshake = (
                    datetime.fromtimestamp(last_handshake_ts, tz=timezone.utc)
                    if last_handshake_ts > 0
                    else None
                )
            except (ValueError, IndexError):
                last_handshake = None

            try:
                rx_bytes = int(parts[5])
                tx_bytes = int(parts[6])
            except (ValueError, IndexError):
                rx_bytes = 0
                tx_bytes = 0

            peers.append(
                PeerTraffic(
                    public_key=public_key,
                    transfer_rx=rx_bytes,
                    transfer_tx=tx_bytes,
                    last_handshake=last_handshake,
                    endpoint=endpoint,
                    allowed_ips=allowed_ips_raw or None,
                )
            )

        return peers

    @staticmethod
    def poll_account_traffic(
        account: VpnAccount,
        *,
        interface: str = DEFAULT_WG_INTERFACE,
    ) -> PeerTraffic | None:
        """
        Poll traffic for a specific account by matching its public key.

        Args:
            account: VpnAccount with public_key.
            interface: WireGuard interface name.

        Returns:
            PeerTraffic if the peer is found, else None.
        """
        if not account.public_key:
            return None

        peers = WireGuardService.poll_traffic(interface=interface)
        for peer in peers:
            if peer.public_key == account.public_key:
                return peer
        return None

    # ------------------------------------------------------------------
    # Connection / Disconnection Detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_connections(
        *,
        interface: str = DEFAULT_WG_INTERFACE,
        handshake_timeout_seconds: int = 180,
    ) -> dict[str, bool]:
        """
        Detect which peers are currently connected.

        A peer is considered "connected" if it had a handshake within the
        ``handshake_timeout_seconds`` window.

        Args:
            interface: WireGuard interface name.
            handshake_timeout_seconds: Maximum seconds since last handshake
                to consider the peer "connected".

        Returns:
            Dict mapping public_key -> bool (True if connected).
        """
        peers = WireGuardService.poll_traffic(interface=interface)
        now = datetime.now(tz=timezone.utc)

        result: dict[str, bool] = {}
        for peer in peers:
            if peer.last_handshake is None:
                result[peer.public_key] = False
            else:
                elapsed = (now - peer.last_handshake).total_seconds()
                result[peer.public_key] = elapsed < handshake_timeout_seconds

        return result

    @staticmethod
    def is_peer_connected(
        public_key: str,
        *,
        interface: str = DEFAULT_WG_INTERFACE,
        handshake_timeout_seconds: int = 180,
    ) -> bool:
        """
        Check if a specific peer is currently connected.

        Args:
            public_key: Peer's public key.
            interface: WireGuard interface name.
            handshake_timeout_seconds: Connected threshold in seconds.

        Returns:
            True if the peer had a recent handshake.
        """
        connections = WireGuardService.detect_connections(
            interface=interface,
            handshake_timeout_seconds=handshake_timeout_seconds,
        )
        return connections.get(public_key, False)

    @staticmethod
    def sync_peer(
        server: VpnServer,
        account: VpnAccount,
        *,
        interface: str = DEFAULT_WG_INTERFACE,
    ) -> bool:
        """
        Synchronize a peer's configuration on the server.

        Removes the peer if it exists and re-adds it with the current configuration.
        This is used during peer renewal to ensure server-side config matches
        the account's current state.

        Args:
            server: VpnServer instance with connection details.
            account: VpnAccount instance with peer keys and IP.
            interface: WireGuard interface name.

        Returns:
            True if the peer was successfully synced.
        """

        try:
            # Remove existing peer (ignore if not found)
            try:
                WireGuardService.remove_peer_from_server(
                    server=server,
                    account=account,
                    interface=interface,
                )
            except WireGuardError:
                logger.debug(
                    "Peer %s not found on server %s, will add fresh",
                    account.public_key,
                    server.public_ip,
                )

            # Re-add with current config
            WireGuardService.add_peer_to_server(
                server=server,
                account=account,
                interface=interface,
            )

            logger.info(
                "Synced peer %s on server %s (%s)",
                account.public_key,
                server.public_ip,
                interface,
            )
            return True

        except WireGuardError as exc:
            logger.error(
                "Failed to sync peer %s on server %s: %s",
                account.public_key,
                server.public_ip,
                exc,
            )
            raise


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _wg_bin() -> str:
    """Return the WireGuard binary path (allows override via env var)."""
    import os

    return os.environ.get("WG_BIN", WG_EXECUTABLE)


def _run_wg_command(cmd: list[str]) -> None:
    """Execute a ``wg`` command and raise WireGuardCommandError on failure."""
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("WireGuard command failed: %s\nStderr: %s", cmd, exc.stderr)
        raise WireGuardCommandError(
            f"Command {' '.join(cmd)} failed: {exc.stderr}"
        ) from exc
    except FileNotFoundError as exc:
        raise WireGuardCommandError(
            f"WireGuard binary '{_wg_bin()}' not found"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise WireGuardCommandError(
            f"WireGuard command timed out: {' '.join(cmd)}"
        ) from exc


__all__ = [
    "PeerTraffic",
    "WireGuardCommandError",
    "WireGuardError",
    "WireGuardKeyGenerationError",
    "WireGuardKeyPair",
    "WireGuardService",
]
