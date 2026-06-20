"""
Unit tests for modules/vpn/xray.py – VLESS+REALITY implementation.

Covers:
- Key management (generate_reality_keypair, generate_short_id, generate_uuid_v4)
- Configuration generation (generate_inbound_config, generate_client_config)
- Server config helpers (build_full_server_config, write_server_config)
- Provision / suspend / restore lifecycle
- Config user management (add_user_via_config, remove_user_via_config, sync_users_to_config)
- Process management (start_xray, stop_xray, restart_xray, is_running)
- Traffic log parsing (parse_traffic_from_log, get_user_traffic)
- Fallback mechanism and multi-short-ID support
- _xray_bin helper
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from modules.vpn.xray import (
    DEFAULT_FALLBACK_SNI,
    DEFAULT_FLOW,
    DEFAULT_NETWORK,
    DEFAULT_SECURITY,
    DEFAULT_SHORT_ID_LENGTH,
    DEFAULT_VLESS_PORT,
    RealityKeyPair,
    XrayError,
    XrayKeyGenerationError,
    XrayService,
    XrayTraffic,
    _xray_bin,
)

# ---------------------------------------------------------------------------
# Constants used by tests
# ---------------------------------------------------------------------------

TEST_PRIVATE_KEY = (
    "aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890123456789012345678901234"
)
TEST_PUBLIC_KEY = (
    "zYxWvUtSrQpOnMlKjIhGfEdCbA9876543210987654321098765432109876"
)
TEST_SHORT_ID = "deadbeef"
TEST_UUID = "12345678-1234-5678-9abc-123456789abc"
TEST_SNI = "www.microsoft.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_keypair() -> RealityKeyPair:
    """Return a predictable RealityKeyPair for test use."""
    return RealityKeyPair(
        private_key=TEST_PRIVATE_KEY,
        public_key=TEST_PUBLIC_KEY,
    )


@pytest.fixture()
def mock_vpn_server() -> MagicMock:
    """Create a mock VPN server with typical attributes."""
    server = MagicMock()
    server.id = 1
    server.host = "198.51.100.1"
    server.ip_address = "198.51.100.1"
    server.port = 443
    server.private_key = TEST_PRIVATE_KEY
    server.public_key = TEST_PUBLIC_KEY
    return server


@pytest.fixture()
def mock_vpn_account() -> MagicMock:
    """Create a mock VPN account with typical attributes."""
    account = MagicMock()
    account.id = 100
    account.user_id = 42
    account.server_id = 1
    account.password = ""
    account.protocol_configs = []
    return account


# =========================================================================
# _xray_bin helper
# =========================================================================

class TestXrayBinHelper:
    """Tests for the _xray_bin helper function."""

    def test_default_binary(self) -> None:
        """Verify default binary name."""
        bin_path = _xray_bin()
        assert bin_path == "xray"

    @patch.dict("os.environ", {"XRAY_BIN": "/custom/path/xray"})
    def test_env_override(self) -> None:
        """Verify ``XRAY_BIN`` environment variable override."""
        assert _xray_bin() == "/custom/path/xray"


# =========================================================================
# Reality Key Management
# =========================================================================

class TestKeyManagement:
    """Tests for generate_reality_keypair, generate_short_id, generate_uuid_v4."""

    @patch("modules.vpn.xray.subprocess.run")
    def test_generate_keypair_success(self, mock_run: MagicMock) -> None:
        """Verify successful key generation."""
        mock_run.return_value = MagicMock(
            stdout=f"Private key: {TEST_PRIVATE_KEY}\nPublic key: {TEST_PUBLIC_KEY}\n",
            stderr="",
            returncode=0,
        )
        kp = XrayService.generate_reality_keypair()
        assert kp.private_key == TEST_PRIVATE_KEY
        assert kp.public_key == TEST_PUBLIC_KEY
        mock_run.assert_called_once_with(
            ["xray", "x25519"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

    @patch("modules.vpn.xray.subprocess.run")
    def test_generate_keypair_parse_failure(self, mock_run: MagicMock) -> None:
        """Verify XrayKeyGenerationError when output cannot be parsed."""
        mock_run.return_value = MagicMock(
            stdout="garbage output",
            stderr="",
            returncode=0,
        )
        with pytest.raises(XrayKeyGenerationError):
            XrayService.generate_reality_keypair()

    @patch("modules.vpn.xray.subprocess.run")
    def test_generate_keypair_subprocess_error(self, mock_run: MagicMock) -> None:
        """Verify XrayKeyGenerationError when subprocess fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["xray", "x25519"], stderr="command not found"
        )
        with pytest.raises(XrayKeyGenerationError):
            XrayService.generate_reality_keypair()

    @patch("modules.vpn.xray.subprocess.run")
    def test_generate_keypair_file_not_found(self, mock_run: MagicMock) -> None:
        """Verify XrayKeyGenerationError when binary is missing."""
        mock_run.side_effect = FileNotFoundError("xray not found")
        with pytest.raises(XrayKeyGenerationError):
            XrayService.generate_reality_keypair()

    @patch("modules.vpn.xray.subprocess.run")
    def test_generate_keypair_timeout(self, mock_run: MagicMock) -> None:
        """Verify XrayKeyGenerationError on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["xray", "x25519"], 10)
        with pytest.raises(XrayKeyGenerationError):
            XrayService.generate_reality_keypair()

    def test_generate_short_id_default_length(self) -> None:
        """Verify default-length short ID is hex."""
        sid = XrayService.generate_short_id()
        assert len(sid) == DEFAULT_SHORT_ID_LENGTH
        int(sid, 16)  # must be valid hex

    def test_generate_short_id_custom_length(self) -> None:
        """Verify custom-length short ID."""
        sid = XrayService.generate_short_id(length=16)
        assert len(sid) == 16
        int(sid, 16)

    def test_generate_uuid_v4(self) -> None:
        """Verify UUID v4 is well-formed."""
        uid = XrayService.generate_uuid_v4()
        parts = uid.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert parts[2][0] == "4"  # version nibble


# =========================================================================
# Inbound Configuration Generation
# =========================================================================

class TestGenerateInboundConfig:
    """Tests for XrayService.generate_inbound_config."""

    def test_basic_inbound_structure(self, mock_keypair: RealityKeyPair) -> None:
        """Verify an inbound config has all required top-level fields."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
        )
        assert config["protocol"] == "vless"
        assert config["port"] == DEFAULT_VLESS_PORT
        assert config["listen"] == "0.0.0.0"
        assert config["tag"] == "vless-reality-inbound"
        assert "settings" in config
        assert "streamSettings" in config

    def test_reality_settings_present(self, mock_keypair: RealityKeyPair) -> None:
        """Verify REALITY settings carry the expected private key and short ID."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
        )
        rs = config["streamSettings"]["realitySettings"]
        assert rs["privateKey"] == TEST_PRIVATE_KEY
        assert TEST_SHORT_ID in rs["shortIds"]

    def test_users_propagated(self, mock_keypair: RealityKeyPair) -> None:
        """Verify user list is placed into settings.clients."""
        users = [
            {"id": "user-1", "flow": "xtls-rprx-vision"},
            {"id": "user-2"},
        ]
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            users=users,
        )
        clients = config["settings"]["clients"]
        assert len(clients) == 2
        assert clients[0]["id"] == "user-1"
        assert clients[0]["flow"] == "xtls-rprx-vision"
        # Second user should have flow defaulted if vision enabled
        assert "flow" in clients[1]

    def test_vision_disabled(self, mock_keypair: RealityKeyPair) -> None:
        """Verify no flow is auto-added when enable_vision=False."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            users=[{"id": "no-flow-user"}],
            enable_vision=False,
        )
        client = config["settings"]["clients"][0]
        assert "flow" not in client

    def test_custom_port_and_tag(self, mock_keypair: RealityKeyPair) -> None:
        """Verify port and tag can be overridden."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            port=8443,
            tag="my-custom-inbound",
        )
        assert config["port"] == 8443
        assert config["tag"] == "my-custom-inbound"

    def test_custom_sni(self, mock_keypair: RealityKeyPair) -> None:
        """Verify custom SNI domain appears in dest and realitySettings."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            sni="custom-sni.example.com",
        )
        rs = config["streamSettings"]["realitySettings"]
        assert "custom-sni.example.com" in rs["dest"]
        assert "custom-sni.example.com" in rs["serverNames"]

    def test_fallback_sni_present(self, mock_keypair: RealityKeyPair) -> None:
        """Verify fallback SNI appears as a fallback dest."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            fallback_sni=DEFAULT_FALLBACK_SNI,
        )
        assert "fallbacks" in config
        assert any(
            DEFAULT_FALLBACK_SNI in fb.get("dest", "")
            for fb in config["fallbacks"]
        )

    def test_no_fallback_when_empty(self, mock_keypair: RealityKeyPair) -> None:
        """Verify no fallbacks entry when fallback_sni is empty string."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            fallback_sni="",
        )
        assert "fallbacks" not in config


# =========================================================================
# Client Configuration Generation
# =========================================================================

class TestGenerateClientConfig:
    """Tests for XrayService.generate_client_config."""

    def test_returns_json_string(self, mock_keypair: RealityKeyPair) -> None:
        """Verify the output is valid JSON."""
        cfg_json = XrayService.generate_client_config(
            server_address="198.51.100.1",
            user_id=TEST_UUID,
            reality_public_key=mock_keypair.public_key,
            short_id=TEST_SHORT_ID,
        )
        parsed = json.loads(cfg_json)
        assert isinstance(parsed, dict)

    def test_basic_client_structure(self, mock_keypair: RealityKeyPair) -> None:
        """Verify output contains expected VLESS outbound keys."""
        cfg_json = XrayService.generate_client_config(
            server_address="vpn.example.com",
            server_port=443,
            user_id=TEST_UUID,
            reality_public_key=mock_keypair.public_key,
            short_id=TEST_SHORT_ID,
            sni="www.microsoft.com",
            fingerprint="chrome",
            flow="xtls-rprx-vision",
        )
        cfg = json.loads(cfg_json)
        assert "outbounds" in cfg
        vless = cfg["outbounds"][0]
        assert vless["protocol"] == "vless"
        settings = vless["settings"]["vnext"][0]
        assert settings["address"] == "vpn.example.com"
        assert settings["port"] == 443
        assert settings["users"][0]["id"] == TEST_UUID

    def test_includes_reality_settings(self, mock_keypair: RealityKeyPair) -> None:
        """Verify public key and short ID appear in Reality stream settings."""
        cfg_json = XrayService.generate_client_config(
            server_address="198.51.100.1",
            user_id=TEST_UUID,
            reality_public_key=mock_keypair.public_key,
            short_id=TEST_SHORT_ID,
        )
        cfg = json.loads(cfg_json)
        vless = cfg["outbounds"][0]
        rs = vless["streamSettings"]["realitySettings"]
        assert rs["publicKey"] == TEST_PUBLIC_KEY
        assert rs["shortId"] == TEST_SHORT_ID

    def test_custom_fingerprint(self, mock_keypair: RealityKeyPair) -> None:
        """Verify fingerprint is passed through."""
        cfg_json = XrayService.generate_client_config(
            server_address="198.51.100.1",
            user_id=TEST_UUID,
            reality_public_key=mock_keypair.public_key,
            short_id=TEST_SHORT_ID,
            fingerprint="firefox",
        )
        cfg = json.loads(cfg_json)
        rs = cfg["outbounds"][0]["streamSettings"]["realitySettings"]
        assert rs["fingerprint"] == "firefox"

    def test_defaults_when_not_provided(self, mock_keypair: RealityKeyPair) -> None:
        """Verify sensible defaults are used when optional args are omitted."""
        cfg_json = XrayService.generate_client_config(
            server_address="198.51.100.1",
            user_id=TEST_UUID,
            reality_public_key=mock_keypair.public_key,
            short_id=TEST_SHORT_ID,
        )
        cfg = json.loads(cfg_json)
        vless = cfg["outbounds"][0]
        assert vless["streamSettings"]["network"] == DEFAULT_NETWORK
        assert vless["streamSettings"]["security"] == DEFAULT_SECURITY

    def test_includes_routing_and_inbounds(self, mock_keypair: RealityKeyPair) -> None:
        """Verify inbounds and routing blocks are present."""
        cfg_json = XrayService.generate_client_config(
            server_address="198.51.100.1",
            user_id=TEST_UUID,
            reality_public_key=mock_keypair.public_key,
            short_id=TEST_SHORT_ID,
        )
        cfg = json.loads(cfg_json)
        assert "routing" in cfg
        assert "inbounds" in cfg


# =========================================================================
# Server Configuration Helpers
# =========================================================================

class TestServerConfig:
    """Tests for build_full_server_config and write_server_config."""

    def test_build_full_server_config(self, mock_keypair: RealityKeyPair) -> None:
        """Verify a full server config has all top-level keys."""
        config = XrayService.build_full_server_config(
            reality_keypair=mock_keypair,
            short_id=TEST_SHORT_ID,
            sni=TEST_SNI,
        )
        assert "log" in config
        assert "inbounds" in config
        assert "outbounds" in config
        assert "routing" in config
        assert "stats" in config
        assert "policy" in config
        assert "api" in config

    def test_build_full_config_with_users(self, mock_keypair: RealityKeyPair) -> None:
        """Verify users are included in the VLESS inbound."""
        users = [{"id": "test-uuid", "flow": DEFAULT_FLOW}]
        config = XrayService.build_full_server_config(
            reality_keypair=mock_keypair,
            short_id=TEST_SHORT_ID,
            users=users,
        )
        vless_inbounds = [
            i for i in config["inbounds"] if i.get("protocol") == "vless"
        ]
        assert len(vless_inbounds) >= 1
        clients = vless_inbounds[0]["settings"]["clients"]
        assert clients[0]["id"] == "test-uuid"

    def test_write_server_config(self, tmp_path: Path) -> None:
        """Verify server config is written to disk."""
        config = XrayService.build_full_server_config()
        path = XrayService.write_server_config(config, config_dir=tmp_path)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert "inbounds" in loaded

    def test_write_server_config_custom_path(self, tmp_path: Path) -> None:
        """Verify custom config path works."""
        config = {"log": {"loglevel": "debug"}}
        custom = tmp_path / "custom_xray.json"
        path = XrayService.write_server_config(config, config_path=custom)
        assert path == custom
        assert custom.exists()

    def test_write_server_config_creates_dirs(self, tmp_path: Path) -> None:
        """Verify parent directories are created automatically."""
        config = {"log": {"loglevel": "info"}}
        deep = tmp_path / "deep" / "nested" / "config.json"
        XrayService.write_server_config(config, config_path=deep)
        assert deep.exists()


# =========================================================================
# Config User Management (add_user_via_config / remove_user_via_config)
# =========================================================================

class TestConfigUserManagement:
    """Tests for add_user_via_config, remove_user_via_config, sync_users_to_config."""

    def _sample_config(
        self,
        user_ids: list[str] | None = None,
        inbound_tag: str = "vless-reality",
    ) -> dict[str, Any]:
        """Build a minimal config for mutation tests."""
        clients = [
            {"id": uid, "flow": DEFAULT_FLOW, "encryption": "none", "level": 0}
            for uid in (user_ids or [])
        ]
        return {
            "inbounds": [
                {
                    "tag": inbound_tag,
                    "port": 443,
                    "protocol": "vless",
                    "settings": {"clients": clients},
                }
            ]
        }

    def test_add_user_via_config_append(self) -> None:
        """Verify a new user is appended to the client list."""
        config = self._sample_config(user_ids=["existing-user"])
        result = XrayService.add_user_via_config(
            config_data=config,
            user_id="new-user",
            inbound_tag="vless-reality",
        )
        clients = result["inbounds"][0]["settings"]["clients"]
        assert len(clients) == 2
        client_ids = [c["id"] for c in clients]
        assert "existing-user" in client_ids
        assert "new-user" in client_ids

    def test_add_user_custom_tag(self) -> None:
        """Verify the inbound_tag parameter selects the correct inbound."""
        config = {
            "inbounds": [
                {"tag": "other-in", "settings": {"clients": []}},
                {
                    "tag": "reality-inbound",
                    "protocol": "vless",
                    "settings": {"clients": [{"id": "existing"}]},
                },
            ]
        }
        result = XrayService.add_user_via_config(
            config_data=config,
            user_id="added",
            inbound_tag="reality-inbound",
        )
        assert len(config["inbounds"][0]["settings"]["clients"]) == 0
        assert len(result["inbounds"][1]["settings"]["clients"]) == 2

    def test_add_user_no_matching_inbound_raises(self) -> None:
        """Verify XrayConfigError when inbound_tag is not found."""
        config = self._sample_config(inbound_tag="some-other-tag")
        with pytest.raises(XrayError):
            XrayService.add_user_via_config(
                config_data=config,
                user_id="user",
                inbound_tag="nonexistent-tag",
            )

    def test_remove_user_via_config(self) -> None:
        """Verify a user is removed from the client list."""
        config = self._sample_config(user_ids=["keep-me", "remove-me"])
        result = XrayService.remove_user_via_config(
            config_data=config,
            user_id="remove-me",
            inbound_tag="vless-reality",
        )
        clients = result["inbounds"][0]["settings"]["clients"]
        assert len(clients) == 1
        assert clients[0]["id"] == "keep-me"

    def test_remove_user_last_client(self) -> None:
        """Verify removing the last client results in an empty list."""
        config = self._sample_config(user_ids=["lonely-user"])
        result = XrayService.remove_user_via_config(
            config_data=config,
            user_id="lonely-user",
            inbound_tag="vless-reality",
        )
        clients = result["inbounds"][0]["settings"]["clients"]
        assert clients == []

    def test_sync_users_replaces_all(self) -> None:
        """Verify sync_users_to_config replaces all users."""
        config = self._sample_config(user_ids=["old-1", "old-2"])
        accounts = [
            {"id": "new-1", "email": "a@b.com"},
            {"id": "new-2"},
        ]
        result = XrayService.sync_users_to_config(
            accounts=accounts,
            config_data=config,
            inbound_tag="vless-reality",
        )
        clients = result["inbounds"][0]["settings"]["clients"]
        ids = [c["id"] for c in clients]
        assert ids == ["new-1", "new-2"]


# =========================================================================
# Provision Account
# =========================================================================

class TestProvisionAccount:
    """Tests for XrayService.provision_account."""

    @patch("modules.vpn.xray.XrayService.generate_reality_keypair")
    def test_provision_success_no_existing_key(
        self,
        mock_gen_kp: MagicMock,
    ) -> None:
        """Verify provision generates keys when server has none, and returns result dict."""
        from unittest.mock import MagicMock as M

        server = M()
        server.id = 1
        server.host = "198.51.100.1"
        server.ip_address = None
        server.port = 443
        server.private_key = ""
        server.public_key = ""

        account = M()
        account.id = 100
        account.password = ""
        account.protocol_configs = []

        mock_gen_kp.return_value = RealityKeyPair(
            private_key=TEST_PRIVATE_KEY,
            public_key=TEST_PUBLIC_KEY,
        )

        result = XrayService.provision_account(server=server, account=account)

        mock_gen_kp.assert_called_once()
        assert "user_id" in result
        assert "client_config" in result
        assert "reality_config" in result
        assert result["reality_config"]["private_key"] == TEST_PRIVATE_KEY
        assert result["reality_config"]["public_key"] == TEST_PUBLIC_KEY

    def test_provision_with_existing_password(self) -> None:
        """Verify account.password is used as user_id when set."""
        from unittest.mock import MagicMock as M

        server = M()
        server.host = "10.0.0.1"
        server.ip_address = None
        server.port = 8443
        server.private_key = TEST_PRIVATE_KEY
        server.public_key = TEST_PUBLIC_KEY

        account = M()
        account.password = TEST_UUID
        account.protocol_configs = []

        result = XrayService.provision_account(server=server, account=account)

        assert result["user_id"] == TEST_UUID

    def test_provision_with_protocol_configs(self) -> None:
        """Verify protocol_configs override SNI and short_id."""
        from unittest.mock import MagicMock as M

        server = M()
        server.host = "10.0.0.1"
        server.ip_address = None
        server.port = 8443
        server.private_key = TEST_PRIVATE_KEY
        server.public_key = TEST_PUBLIC_KEY

        cfg_sni = M()
        cfg_sni.config_key = "sni"
        cfg_sni.config_value = "custom-sni.example.com"

        cfg_sid = M()
        cfg_sid.config_key = "short_id"
        cfg_sid.config_value = "abcd1234"

        account = M()
        account.password = ""
        account.protocol_configs = [cfg_sni, cfg_sid]

        result = XrayService.provision_account(server=server, account=account)
        assert result["reality_config"]["sni"] == "custom-sni.example.com"
        assert result["reality_config"]["short_id"] == "abcd1234"

    @patch("modules.vpn.xray.XrayService.generate_reality_keypair",
           side_effect=XrayKeyGenerationError("keygen failed"))
    def test_provision_keygen_failure(
        self,
        mock_gen_kp: MagicMock,
    ) -> None:
        """Verify XrayKeyGenerationError propagates from provision_account."""
        from unittest.mock import MagicMock as M

        server = M()
        server.host = "10.0.0.1"
        server.ip_address = None
        server.port = 443
        server.private_key = ""
        server.public_key = ""

        account = M()
        account.password = ""
        account.protocol_configs = []

        with pytest.raises(XrayKeyGenerationError):
            XrayService.provision_account(server=server, account=account)


# =========================================================================
# Suspend Account
# =========================================================================

class TestSuspendAccount:
    """Tests for XrayService.suspend_account."""

    def test_suspend_no_password(self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock) -> None:
        """Verify suspend returns failure when account has no password."""
        mock_vpn_account.password = ""
        result = XrayService.suspend_account(
            server=mock_vpn_server,
            account=mock_vpn_account,
        )
        assert result["success"] is False
        assert "No UUID" in result["message"]

    def test_suspend_config_not_found(
        self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock, tmp_path: Path
    ) -> None:
        """Verify suspend when config file doesn't exist."""

        mock_vpn_account.password = TEST_UUID
        with patch("modules.vpn.xray.DEFAULT_XRAY_CONFIG_DIR", tmp_path):
            result = XrayService.suspend_account(
                server=mock_vpn_server,
                account=mock_vpn_account,
            )
        assert result["success"] is True
        assert "not present" in result["message"]

    def test_suspend_removes_user_from_config(
        self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock, tmp_path: Path
    ) -> None:
        """Verify suspend removes user from config file."""
        mock_vpn_account.password = TEST_UUID
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "inbounds": [
                {
                    "tag": "vless-reality",
                    "protocol": "vless",
                    "settings": {
                        "clients": [
                            {"id": TEST_UUID, "flow": DEFAULT_FLOW},
                            {"id": "other-user", "flow": DEFAULT_FLOW},
                        ]
                    },
                }
            ]
        }
        config_path.write_text(json.dumps(config))

        with patch("modules.vpn.xray.DEFAULT_XRAY_CONFIG_DIR", tmp_path):
            result = XrayService.suspend_account(
                server=mock_vpn_server,
                account=mock_vpn_account,
            )

        assert result["success"] is True
        # Verify the user was removed from the written file
        updated = json.loads(config_path.read_text())
        clients = updated["inbounds"][0]["settings"]["clients"]
        ids = [c["id"] for c in clients]
        assert TEST_UUID not in ids
        assert "other-user" in ids

    def test_suspend_user_not_found(
        self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock, tmp_path: Path
    ) -> None:
        """Verify suspend when user is not in config."""
        mock_vpn_account.password = TEST_UUID
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "inbounds": [
                {
                    "tag": "vless-reality",
                    "protocol": "vless",
                    "settings": {"clients": [{"id": "other-user", "flow": DEFAULT_FLOW}]},
                }
            ]
        }
        config_path.write_text(json.dumps(config))

        with patch("modules.vpn.xray.DEFAULT_XRAY_CONFIG_DIR", tmp_path):
            result = XrayService.suspend_account(
                server=mock_vpn_server,
                account=mock_vpn_account,
            )

        assert result["success"] is True
        assert "not found" in result["message"]


# =========================================================================
# Restore Account
# =========================================================================

class TestRestoreAccount:
    """Tests for XrayService.restore_account."""

    def test_restore_no_password(self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock) -> None:
        """Verify restore returns failure when account has no password."""
        mock_vpn_account.password = ""
        result = XrayService.restore_account(
            server=mock_vpn_server,
            account=mock_vpn_account,
        )
        assert result["success"] is False
        assert "No UUID" in result["message"]

    def test_restore_config_not_found_creates_new(
        self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock, tmp_path: Path
    ) -> None:
        """Verify restore creates a new config when none exists."""
        mock_vpn_account.password = TEST_UUID
        mock_vpn_server.port = 8443
        mock_vpn_server.private_key = TEST_PRIVATE_KEY
        mock_vpn_server.ip_address = None

        config_subdir = tmp_path / "config_sub"
        config_subdir.mkdir(parents=True, exist_ok=True)

        with patch("modules.vpn.xray.DEFAULT_XRAY_CONFIG_DIR", config_subdir):
            with patch("modules.vpn.xray.XrayService.generate_reality_keypair") as mock_kp:
                mock_kp.return_value = RealityKeyPair(
                    private_key=TEST_PRIVATE_KEY,
                    public_key=TEST_PUBLIC_KEY,
                )
                result = XrayService.restore_account(
                    server=mock_vpn_server,
                    account=mock_vpn_account,
                )

        assert result["success"] is True
        assert "New config created" in result["message"]
        assert (config_subdir / "config.json").exists()

    def test_restore_adds_user_to_existing_config(
        self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock, tmp_path: Path
    ) -> None:
        """Verify restore adds user to an existing config."""
        mock_vpn_account.password = TEST_UUID
        mock_vpn_server.port = 443
        mock_vpn_server.private_key = TEST_PRIVATE_KEY
        mock_vpn_server.public_key = TEST_PUBLIC_KEY

        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "inbounds": [
                {
                    "tag": "vless-reality",
                    "protocol": "vless",
                    "settings": {"clients": [{"id": "existing-user", "flow": DEFAULT_FLOW}]},
                }
            ]
        }
        config_path.write_text(json.dumps(config))

        with patch("modules.vpn.xray.DEFAULT_XRAY_CONFIG_DIR", tmp_path):
            result = XrayService.restore_account(
                server=mock_vpn_server,
                account=mock_vpn_account,
            )

        assert result["success"] is True
        updated = json.loads(config_path.read_text())
        clients = updated["inbounds"][0]["settings"]["clients"]
        ids = [c["id"] for c in clients]
        assert "existing-user" in ids
        assert TEST_UUID in ids

    def test_restore_user_already_exists(
        self, mock_vpn_server: MagicMock, mock_vpn_account: MagicMock, tmp_path: Path
    ) -> None:
        """Verify restore when user is already in config."""
        mock_vpn_account.password = TEST_UUID
        mock_vpn_server.port = 443
        mock_vpn_server.private_key = TEST_PRIVATE_KEY
        mock_vpn_server.public_key = TEST_PUBLIC_KEY

        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "inbounds": [
                {
                    "tag": "vless-reality",
                    "protocol": "vless",
                    "settings": {"clients": [{"id": TEST_UUID, "flow": DEFAULT_FLOW}]},
                }
            ]
        }
        config_path.write_text(json.dumps(config))

        with patch("modules.vpn.xray.DEFAULT_XRAY_CONFIG_DIR", tmp_path):
            result = XrayService.restore_account(
                server=mock_vpn_server,
                account=mock_vpn_account,
            )

        assert result["success"] is True
        assert "already present" in result["message"]


# =========================================================================
# Traffic Statistics
# =========================================================================

class TestTrafficParsing:
    """Tests for parse_traffic_from_log and get_user_traffic."""

    @pytest.fixture()
    def sample_log_content(self) -> str:
        """Sample Xray access log content in the format the parser expects."""
        return (
            "2026/06/14 10:00:00 email: user-uuid-1 uplink 2048\n"
            "2026/06/14 10:00:00 email: user-uuid-1 downlink 1024\n"
            "2026/06/14 10:01:00 email: user-uuid-2 uplink 4096\n"
            "2026/06/14 10:02:00 email: user-uuid-1 uplink 1024\n"
        )

    def test_parse_traffic_log_basic(self, tmp_path: Path, sample_log_content: str) -> None:
        """Verify traffic log parser extracts stats per user."""
        log_file = tmp_path / "access.log"
        log_file.write_text(sample_log_content)

        traffic_list = XrayService.parse_traffic_from_log(
            log_path=str(log_file),
            recent_seconds=999999,
        )

        # user-uuid-1 should be aggregated
        uuids = [t.user_id for t in traffic_list]
        assert "user-uuid-1" in uuids
        assert "user-uuid-2" in uuids

    def test_parse_traffic_empty_log(self, tmp_path: Path) -> None:
        """Verify empty log returns empty list."""
        log_file = tmp_path / "access.log"
        log_file.write_text("")

        traffic_list = XrayService.parse_traffic_from_log(str(log_file))
        assert traffic_list == []

    def test_parse_traffic_nonexistent_file(self) -> None:
        """Verify nonexistent log file returns empty list."""
        traffic_list = XrayService.parse_traffic_from_log("/nonexistent/path/access.log")
        assert traffic_list == []

    def test_get_user_traffic_found(self, tmp_path: Path, sample_log_content: str) -> None:
        """Verify get_user_traffic returns XrayTraffic for a specific user."""
        log_file = tmp_path / "access.log"
        log_file.write_text(sample_log_content)

        traffic = XrayService.get_user_traffic(
            user_id="user-uuid-1",
            log_path=str(log_file),
            recent_seconds=999999,
        )
        assert traffic is not None
        assert isinstance(traffic, XrayTraffic)
        assert traffic.user_id == "user-uuid-1"
        assert traffic.total > 0

    def test_get_user_traffic_no_data(self, tmp_path: Path) -> None:
        """Verify None is returned when user has no traffic."""
        log_file = tmp_path / "access.log"
        log_file.write_text("")
        traffic = XrayService.get_user_traffic(
            user_id="nonexistent-user",
            log_path=str(log_file),
        )
        assert traffic is None


# =========================================================================
# Fallback Mechanism
# =========================================================================

class TestFallbackMechanism:
    """Tests for fallback SNI handling in config generation."""

    def test_fallback_sni_in_inbound(self, mock_keypair: RealityKeyPair) -> None:
        """Verify fallback SNI appears in fallback destinations."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            fallback_sni=DEFAULT_FALLBACK_SNI,
        )
        assert "fallbacks" in config
        assert any(
            DEFAULT_FALLBACK_SNI in f.get("dest", "") for f in config["fallbacks"]
        )

    def test_no_fallback_when_not_set(self, mock_keypair: RealityKeyPair) -> None:
        """Verify no fallbacks when fallback_sni is empty."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
            fallback_sni="",
        )
        assert "fallbacks" not in config

    def test_short_id_in_short_ids(self, mock_keypair: RealityKeyPair) -> None:
        """Verify shortId appears in realitySettings.shortIds."""
        config = XrayService.generate_inbound_config(
            reality_private_key=mock_keypair.private_key,
            short_id=TEST_SHORT_ID,
        )
        rs = config["streamSettings"]["realitySettings"]
        assert TEST_SHORT_ID in rs["shortIds"]


# =========================================================================
# Process Management
# =========================================================================

class TestProcessManagement:
    """Tests for start_xray, stop_xray, restart_xray, is_running."""

    @patch("modules.vpn.xray.subprocess.Popen")
    def test_start_xray_returns_popen(self, mock_popen: MagicMock) -> None:
        """Verify start_xray returns a Popen handle."""
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc

        proc = XrayService.start_xray(config_path="/fake/config.json")

        assert proc is mock_proc
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "xray" in args[0]
        assert args[1] == "run"

    @patch("modules.vpn.xray.subprocess.Popen")
    def test_start_xray_file_not_found(self, mock_popen: MagicMock) -> None:
        """Verify XrayCommandError when binary is missing."""
        mock_popen.side_effect = FileNotFoundError("xray not found")
        with pytest.raises(XrayError):
            XrayService.start_xray(config_path="/fake/config.json")

    @patch("modules.vpn.xray.subprocess.run")
    def test_stop_xray_windows(self, mock_run: MagicMock) -> None:
        """Verify stop_xray uses taskkill on Windows."""
        with patch("modules.vpn.xray.os.name", "nt"):
            XrayService.stop_xray(pid=99999)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "taskkill" in args

    def test_stop_xray_no_pid(self) -> None:
        """Verify stop_xray with no pid doesn't raise."""
        XrayService.stop_xray(None, pid=None)

    @patch("modules.vpn.xray.XrayService.start_xray")
    @patch("modules.vpn.xray.XrayService.stop_xray")
    def test_restart_xray(
        self,
        mock_stop: MagicMock,
        mock_start: MagicMock,
    ) -> None:
        """Verify restart stops old proc and starts new."""
        old_proc = MagicMock()
        new_proc = MagicMock()
        mock_start.return_value = new_proc

        result = XrayService.restart_xray(
            config_path="/fake/config.json",
            old_proc=old_proc,
        )

        mock_stop.assert_called_once_with(old_proc)
        mock_start.assert_called_once_with(config_path="/fake/config.json")
        assert result is new_proc

    def test_is_running_returns_false_for_none(self) -> None:
        """Verify is_running returns False with no arguments."""
        assert XrayService.is_running() is False


# =========================================================================
# Integration-Style: Config Generation Round-Trip
# =========================================================================

class TestConfigRoundTrip:
    """Higher-level tests that exercise multiple methods together."""

    def test_inbound_then_build_and_write(self, tmp_path: Path, mock_keypair: RealityKeyPair) -> None:
        """Verify a full config can be generated and written."""
        config = XrayService.build_full_server_config(
            reality_keypair=mock_keypair,
            short_id=TEST_SHORT_ID,
            port=8443,
        )
        path = XrayService.write_server_config(config, config_dir=tmp_path)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["inbounds"][0]["port"] == 8443

    def test_add_user_to_generated_config(self, mock_keypair: RealityKeyPair) -> None:
        """Verify user can be added to a generated inbound."""
        config = XrayService.build_full_server_config(
            reality_keypair=mock_keypair,
            short_id=TEST_SHORT_ID,
            users=[{"id": "initial-user", "flow": DEFAULT_FLOW}],
        )
        # The tag used by build_full_server_config is "vless-reality"
        result = XrayService.add_user_via_config(
            config_data=config,
            user_id="added-user",
            inbound_tag="vless-reality",
        )
        clients = result["inbounds"][0]["settings"]["clients"]
        ids = [c["id"] for c in clients]
        assert "initial-user" in ids
        assert "added-user" in ids
