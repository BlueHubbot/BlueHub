"""
BlueHub Module Registry Unit Tests
====================================
Tests for module metadata, service, schemas, and feature flag
dependencies. Uses pytest-asyncio and mocking for database interactions.

Run: pytest tests/unit/test_module_registry.py -v --asyncio-mode=auto
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.registry.schemas import (
    ModuleFlag,
    ModuleMetadata,
    ModuleRegistryResponse,
    ModuleStatus,
    ModuleToggleRequest,
)
from core.registry.service import (
    ModuleRegistryService,
    module_registry_service,
)
from shared.models.module_registry import ModuleRegistry

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_metadata() -> ModuleMetadata:
    """Sample module metadata fixture."""
    return ModuleMetadata(
        name="test_module",
        display_name="Test Module",
        description="A test module for unit testing",
        version="2.0.0",
        order=10,
        config_schema={"type": "object", "properties": {}},
        default_flags=ModuleFlag(
            enabled=True,
            stop_new_sales=False,
            terminate_services=False,
            maintenance_mode=False,
        ),
        dependencies=["core"],
        icon="test-icon",
        tags=["test", "unit"],
    )


@pytest.fixture()
def sample_module_registry() -> ModuleRegistry:
    """Sample ModuleRegistry ORM instance fixture."""
    return ModuleRegistry(
        id="123e4567-e89b-12d3-a456-426614174000",
        module_name="vpn",
        display_name="VPN Service",
        description="Virtual Private Network services",
        version="1.0.0",
        enabled=True,
        order=1,
        config_schema={"type": "object"},
        flags={
            "enabled": True,
            "stop_new_sales": False,
            "terminate_services": False,
            "maintenance_mode": False,
        },
    )


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


# ── Schema Tests ───────────────────────────────────────────────────────────


class TestModuleStatus:
    """Tests for ModuleStatus enum."""

    def test_values(self) -> None:
        """Test enum values match expected strings."""
        assert ModuleStatus.ACTIVE.value == "active"
        assert ModuleStatus.STOP_NEW_SALES.value == "stop_new_sales"
        assert ModuleStatus.TERMINATE_SERVICES.value == "terminate_services"
        assert ModuleStatus.DISABLED.value == "disabled"


class TestModuleFlag:
    """Tests for ModuleFlag model."""

    def test_default_values(self) -> None:
        """Test default flag values."""
        flags = ModuleFlag()
        assert flags.enabled is True
        assert flags.stop_new_sales is False
        assert flags.terminate_services is False
        assert flags.maintenance_mode is False

    def test_custom_values(self) -> None:
        """Test custom flag values."""
        flags = ModuleFlag(
            enabled=False,
            stop_new_sales=True,
            terminate_services=True,
        )
        assert flags.enabled is False
        assert flags.stop_new_sales is True
        assert flags.terminate_services is True
        assert flags.maintenance_mode is False  # default


class TestModuleMetadata:
    """Tests for ModuleMetadata model."""

    def test_required_fields(self, sample_metadata: ModuleMetadata) -> None:
        """Test that required fields are set correctly."""
        assert sample_metadata.name == "test_module"
        assert sample_metadata.display_name == "Test Module"

    def test_optional_defaults(self) -> None:
        """Test optional fields get proper defaults."""
        meta = ModuleMetadata(name="minimal", display_name="Minimal")
        assert meta.description == ""
        assert meta.version == "1.0.0"
        assert meta.order == 0
        assert meta.config_schema is None
        assert meta.default_flags.enabled is True
        assert meta.dependencies == []
        assert meta.icon is None
        assert meta.tags == []

    def test_custom_optional_fields(self, sample_metadata: ModuleMetadata) -> None:
        """Test optional fields with custom values."""
        assert sample_metadata.version == "2.0.0"
        assert sample_metadata.order == 10
        assert sample_metadata.config_schema is not None
        assert sample_metadata.icon == "test-icon"
        assert sample_metadata.tags == ["test", "unit"]


class TestModuleRegistryResponse:
    """Tests for ModuleRegistryResponse model."""

    def test_from_fields(self) -> None:
        """Test creating response from fields."""
        response = ModuleRegistryResponse(
            id="test-id",
            module_name="vpn",
            display_name="VPN Service",
            description="VPN description",
            version="1.0.0",
            enabled=True,
            order=1,
            flags=ModuleFlag(),
        )
        assert response.module_name == "vpn"
        assert response.enabled is True
        assert response.flags.enabled is True

    def test_optional_id(self) -> None:
        """Test that id is optional."""
        response = ModuleRegistryResponse(
            module_name="vpn",
            display_name="VPN",
            version="1.0.0",
            enabled=True,
        )
        assert response.id is None


class TestModuleToggleRequest:
    """Tests for ModuleToggleRequest model."""

    def test_all_optional(self) -> None:
        """Test all fields are optional."""
        request = ModuleToggleRequest()
        assert request.enabled is None
        assert request.stop_new_sales is None

    def test_partial_update(self) -> None:
        """Test partial update with only some fields."""
        request = ModuleToggleRequest(enabled=False)
        assert request.enabled is False
        assert request.stop_new_sales is None


# ── Service Tests ─────────────────────────────────────────────────────────


class TestModuleRegistryService:
    """Tests for ModuleRegistryService."""

    @pytest.mark.asyncio()
    async def test_get_all_modules_empty(
        self, mock_session: AsyncMock
    ) -> None:
        """Test get_all_modules returns empty list when no modules registered."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        modules = await service.get_all_modules(session=mock_session)

        assert modules == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_get_all_modules_with_data(
        self, mock_session: AsyncMock, sample_module_registry: ModuleRegistry
    ) -> None:
        """Test get_all_modules returns registered modules."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [
            sample_module_registry
        ]
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        modules = await service.get_all_modules(session=mock_session)

        assert len(modules) == 1
        assert modules[0].module_name == "vpn"

    @pytest.mark.asyncio()
    async def test_is_module_enabled_db_fallback(
        self, mock_session: AsyncMock
    ) -> None:
        """Test is_module_enabled falls back to DB when Redis is unavailable."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = True
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        enabled = await service.is_module_enabled(
            "vpn", session=mock_session
        )

        assert enabled is True

    @pytest.mark.asyncio()
    async def test_is_module_enabled_not_found(
        self, mock_session: AsyncMock
    ) -> None:
        """Test is_module_enabled defaults to True when module not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        enabled = await service.is_module_enabled(
            "nonexistent", session=mock_session
        )

        assert enabled is True  # Default to enabled

    @pytest.mark.asyncio()
    async def test_is_module_enabled_false(
        self, mock_session: AsyncMock
    ) -> None:
        """Test is_module_enabled returns False when module is disabled."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = False
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        enabled = await service.is_module_enabled(
            "disabled_mod", session=mock_session
        )

        assert enabled is False

    @pytest.mark.asyncio()
    async def test_get_module_flags(
        self, mock_session: AsyncMock, sample_module_registry: ModuleRegistry
    ) -> None:
        """Test get_module_flags returns correct flags."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_module_registry
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        flags = await service.get_module_flags("vpn", session=mock_session)

        assert flags.enabled is True
        assert flags.stop_new_sales is False

    @pytest.mark.asyncio()
    async def test_get_module_flags_not_found(
        self, mock_session: AsyncMock
    ) -> None:
        """Test get_module_flags returns defaults when module not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        flags = await service.get_module_flags(
            "nonexistent", session=mock_session
        )

        assert flags.enabled is True
        assert flags.stop_new_sales is False

    @pytest.mark.asyncio()
    async def test_toggle_module_not_found(
        self, mock_session: AsyncMock
    ) -> None:
        """Test toggle_module returns None for non-existent module."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        request = ModuleToggleRequest(enabled=False)
        result = await service.toggle_module(
            "nonexistent", request, session=mock_session
        )

        assert result is None

    @pytest.mark.asyncio()
    async def test_toggle_module_disabled(
        self, mock_session: AsyncMock, sample_module_registry: ModuleRegistry
    ) -> None:
        """Test toggle_module disables a module."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_module_registry
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        request = ModuleToggleRequest(enabled=False)
        result = await service.toggle_module(
            "vpn", request, session=mock_session
        )

        assert result is not None
        assert result.module_name == "vpn"
        assert result.flags.enabled is False
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_toggle_module_stop_new_sales(
        self, mock_session: AsyncMock, sample_module_registry: ModuleRegistry
    ) -> None:
        """Test toggle_module sets stop_new_sales flag."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_module_registry
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        request = ModuleToggleRequest(stop_new_sales=True)
        result = await service.toggle_module(
            "vpn", request, session=mock_session
        )

        assert result is not None
        assert result.flags.stop_new_sales is True

    @pytest.mark.asyncio()
    async def test_toggle_module_multiple_flags(
        self, mock_session: AsyncMock, sample_module_registry: ModuleRegistry
    ) -> None:
        """Test toggle_module sets multiple flags at once."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sample_module_registry
        mock_session.execute.return_value = result_mock

        service = ModuleRegistryService()
        request = ModuleToggleRequest(
            enabled=False,
            maintenance_mode=True,
        )
        result = await service.toggle_module(
            "vpn", request, session=mock_session
        )

        assert result is not None
        assert result.flags.enabled is False
        assert result.flags.maintenance_mode is True

    # ── _to_response tests ─────────────────────────────────────────

    def test_to_response(
        self, sample_module_registry: ModuleRegistry
    ) -> None:
        """Test _to_response converts ORM to response schema."""
        response = ModuleRegistryService._to_response(sample_module_registry)
        assert isinstance(response, ModuleRegistryResponse)
        assert response.module_name == "vpn"
        assert response.enabled is True
        assert response.flags.enabled is True

    def test_to_response_with_none_id(self) -> None:
        """Test _to_response handles None id."""
        registry = ModuleRegistry(
            module_name="test",
            display_name="Test",
            version="1.0.0",
            enabled=True,
        )
        response = ModuleRegistryService._to_response(registry)
        assert response.id is None

    def test_to_response_empty_flags(self) -> None:
        """Test _to_response handles empty flags dict."""
        registry = ModuleRegistry(
            id="test-id",
            module_name="test",
            display_name="Test",
            version="1.0.0",
            enabled=True,
            flags=None,
        )
        response = ModuleRegistryService._to_response(registry)
        assert response.flags.enabled is True  # default

    # ── Module discovery tests ──────────────────────────────────────

    def test_import_metadata_failure(self) -> None:
        """Test _import_metadata returns None on import failure."""
        service = ModuleRegistryService()
        result = service._import_metadata(
            modules_dir="/nonexistent",
            module_entry="nonexistent_module",
        )
        assert result is None


# ── Metadata File Tests ────────────────────────────────────────────────────


class TestModuleMetadataFiles:
    """Tests that each module's metadata.py is correctly structured."""

    def test_vpn_metadata(self) -> None:
        """Test VPN module metadata."""
        from modules.vpn.metadata import metadata

        assert isinstance(metadata, ModuleMetadata)
        assert metadata.name == "vpn"
        # VPN metadata uses i18n dict for display_name and description
        assert isinstance(metadata.display_name, dict) or metadata.display_name == "VPN Service"
        assert metadata.default_flags.enabled is True

    def test_vps_metadata(self) -> None:
        """Test VPS module metadata."""
        from modules.vps.metadata import metadata

        assert isinstance(metadata, ModuleMetadata)
        assert metadata.name == "vps"
        assert metadata.display_name == "VPS Service"
        assert metadata.default_flags.enabled is True

    def test_smartdns_metadata(self) -> None:
        """Test SmartDNS module metadata."""
        from modules.smartdns.metadata import metadata

        assert isinstance(metadata, ModuleMetadata)
        assert metadata.name == "smartdns"
        assert metadata.display_name == "SmartDNS Service"

    def test_streaming_metadata(self) -> None:
        """Test Streaming module metadata."""
        from modules.streaming.metadata import metadata

        assert isinstance(metadata, ModuleMetadata)
        assert metadata.name == "streaming"
        assert metadata.display_name == "Streaming Service"

    def test_game_metadata(self) -> None:
        """Test Game module metadata."""
        from modules.game.metadata import metadata

        assert isinstance(metadata, ModuleMetadata)
        assert metadata.name == "game"
        assert metadata.display_name == "Game Service"

    def test_all_metadata_have_unique_names(self) -> None:
        """Test all module names are unique."""
        from modules.game.metadata import metadata as game
        from modules.smartdns.metadata import metadata as smartdns
        from modules.streaming.metadata import metadata as streaming
        from modules.vpn.metadata import metadata as vpn
        from modules.vps.metadata import metadata as vps

        names = [vpn.name, vps.name, smartdns.name, streaming.name, game.name]
        assert len(names) == len(set(names)), "Module names must be unique"

    def test_all_metadata_have_unique_orders(self) -> None:
        """Test all module orders are unique."""
        from modules.game.metadata import metadata as game
        from modules.smartdns.metadata import metadata as smartdns
        from modules.streaming.metadata import metadata as streaming
        from modules.vpn.metadata import metadata as vpn
        from modules.vps.metadata import metadata as vps

        orders = [vpn.order, vps.order, smartdns.order, streaming.order, game.order]
        assert len(orders) == len(set(orders)), "Module orders must be unique"


# ── Registry Initialization Tests ──────────────────────────────────────────


class TestModuleRegistrySingleton:
    """Tests for the module_registry_service singleton."""

    def test_singleton_instance(self) -> None:
        """Test that module_registry_service is a ModuleRegistryService."""
        assert isinstance(
            module_registry_service, ModuleRegistryService
        )

    def test_singleton_is_same(self) -> None:
        """Test that importing the singleton gives the same instance."""
        from core.registry.service import (
            module_registry_service as imported_service,
        )

        assert module_registry_service is imported_service


# ── Import Tests ───────────────────────────────────────────────────────────


class TestRegistryImports:
    """Tests correct importing from core.registry."""

    def test_import_all_components(self) -> None:
        """Test all expected exports exist."""
        from core.registry import (
            ModuleFlag,
            ModuleMetadata,
            ModuleRegistryResponse,
            ModuleRegistryService,
            ModuleStatus,
            ModuleToggleRequest,
            module_registry_service,
            require_module,
            require_module_dep,
        )

        assert ModuleFlag is not None
        assert ModuleMetadata is not None
        assert ModuleRegistryResponse is not None
        assert ModuleRegistryService is not None
        assert ModuleStatus is not None
        assert ModuleToggleRequest is not None
        assert module_registry_service is not None
        assert require_module is not None
        assert require_module_dep is not None
