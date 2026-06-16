"""
BlueHub - Telegram Bot Unit Tests
==================================
Tests for bot handlers, middleware, and keyboards.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import Message, CallbackQuery, User as TgUser, Chat
from aiogram.dispatcher.dispatcher import Dispatcher

from bot.middleware.i18n import I18nMiddleware
from bot.middleware.auth import AuthMiddleware
from bot.handlers.start import cmd_start, cmd_language
from bot.handlers.admin import cmd_admin, cmd_stats
from bot.handlers.account import cmd_account
from bot.keyboards.main_menu import build_main_menu
from bot.keyboards.language import (
    build_language_selector,
    build_language_confirmation,
    SUPPORTED_LOCALES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_user():
    """Create a mock database user."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "customer"
    user.language = "en"
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin database user."""
    user = MagicMock()
    user.id = 2
    user.username = "admin"
    user.email = "admin@example.com"
    user.role = "superadmin"
    user.language = "en"
    return user


@pytest.fixture
def mock_tg_user():
    """Create a mock Telegram user."""
    return User(id=12345, is_bot=False, first_name="Test", username="tguser")


@pytest.fixture
def mock_chat():
    """Create a mock chat."""
    return Chat(id=12345, type="private")


@pytest.fixture
def mock_message(mock_tg_user, mock_chat):
    """Create a mock Message with minimal required fields."""
    msg = MagicMock(spec=Message)
    msg.message_id = 100
    msg.from_user = mock_tg_user
    msg.chat = mock_chat
    msg.text = ""
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_callback(mock_tg_user, mock_chat):
    """Create a mock CallbackQuery."""
    cb = MagicMock(spec=CallbackQuery)
    cb.id = "cb_001"
    cb.from_user = mock_tg_user
    cb.message = MagicMock(spec=Message)
    cb.message.chat = mock_chat
    cb.message.message_id = 101
    cb.message.edit_text = AsyncMock()
    cb.message.delete = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.data = ""
    cb.answer = AsyncMock()
    return cb


@pytest.fixture
async def mock_T():
    """Create a mock translation function."""
    async def translate(key, **kwargs):
        translations = {
            "bot.welcome": f"Welcome {kwargs.get('name', 'User')}!",
            "bot.help": "This is the help text.",
            "bot.language": "Change Language",
            "bot.unauthorized": "Unauthorized.",
            "bot.admin_welcome": "Admin Panel",
            "bot.stats_placeholder": "Stats placeholder",
            "bot.account_info": f"Account: {kwargs}",
            "bot.account_not_found": "Account not found",
            "bot.language_select": "Select language:",
            "bot.language_changed": f"Changed to {kwargs.get('locale', 'en')}",
            "bot.language_error": "Error changing language",
            "bot.language_updated": "Language updated",
            "bot.language_done": "Done",
            "bot.services": "Services",
            "bot.account": "Account",
            "bot.support": "Support",
            "bot.admin": "Admin",
            "bot.stats": "Stats",
            "bot.help": "Help",
        }
        return translations.get(key, key)
    return translate


# ---------------------------------------------------------------------------
# Middleware Tests
# ---------------------------------------------------------------------------

class TestI18nMiddleware:
    """Tests for i18n middleware."""

    @pytest.mark.anyio
    async def test_middleware_initialization(self):
        """Test middleware can be initialized."""
        middleware = I18nMiddleware(locales_dir="config/locales")
        assert middleware is not None

    @pytest.mark.anyio
    async def test_middleware_setup(self):
        """Test middleware setup method."""
        middleware = I18nMiddleware(locales_dir="config/locales")
        dp = Dispatcher()
        middleware.setup(dp)
        # Should not raise


class TestAuthMiddleware:
    """Tests for auth middleware."""

    def test_auth_middleware_initialization(self):
        """Test auth middleware can be initialized."""
        middleware = AuthMiddleware()
        assert middleware is not None

    @pytest.mark.anyio
    async def test_auth_middleware_setup(self):
        """Test auth middleware setup."""
        middleware = AuthMiddleware()
        dp = Dispatcher()
        middleware.setup(dp)
        # Should not raise


# ---------------------------------------------------------------------------
# Start Handler Tests
# ---------------------------------------------------------------------------

class TestStartHandler:
    """Tests for /start command handler."""

    @pytest.mark.anyio
    async def test_start_new_user(self, mock_message, mock_T, mock_db_user):
        """Test /start for registered user."""
        await cmd_start(mock_message, mock_T, mock_db_user)

        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert "Welcome" in args[0]

    @pytest.mark.anyio
    async def test_start_no_db_user(self, mock_message, mock_T):
        """Test /start for unregistered user."""
        await cmd_start(mock_message, mock_T, None)

        mock_message.answer.assert_called_once()

    @pytest.mark.anyio
    async def test_language_command(self, mock_message, mock_T):
        """Test /language command shows selector."""
        await cmd_language(mock_message, mock_T)

        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert args[0] == "Select language:"
        assert "reply_markup" in kwargs


# ---------------------------------------------------------------------------
# Admin Handler Tests
# ---------------------------------------------------------------------------

class TestAdminHandler:
    """Tests for admin command handlers."""

    @pytest.mark.anyio
    async def test_admin_unauthorized(self, mock_message, mock_T, mock_db_user):
        """Test /admin for non-admin user."""
        await cmd_admin(mock_message, mock_T, mock_db_user)

        mock_message.answer.assert_called_once_with("Unauthorized.")

    @pytest.mark.anyio
    async def test_admin_authorized(self, mock_message, mock_T, mock_admin_user):
        """Test /admin for admin user."""
        await cmd_admin(mock_message, mock_T, mock_admin_user)

        mock_message.answer.assert_called_once_with("Admin Panel")

    @pytest.mark.anyio
    async def test_admin_no_db_user(self, mock_message, mock_T):
        """Test /admin for unregistered user."""
        await cmd_admin(mock_message, mock_T, None)

        mock_message.answer.assert_called_once_with("Unauthorized.")

    @pytest.mark.anyio
    async def test_stats_unauthorized(self, mock_message, mock_T, mock_db_user):
        """Test /stats for non-admin."""
        await cmd_stats(mock_message, mock_T, mock_db_user)

        mock_message.answer.assert_called_once_with("Unauthorized.")

    @pytest.mark.anyio
    async def test_stats_authorized(self, mock_message, mock_T, mock_admin_user):
        """Test /stats for admin."""
        await cmd_stats(mock_message, mock_T, mock_admin_user)

        mock_message.answer.assert_called_once_with("Stats placeholder")


# ---------------------------------------------------------------------------
# Account Handler Tests
# ---------------------------------------------------------------------------

class TestAccountHandler:
    """Tests for /account handler."""

    @pytest.mark.anyio
    async def test_account_with_user(self, mock_message, mock_T, mock_db_user):
        """Test /account for registered user."""
        await cmd_account(mock_message, mock_T, mock_db_user)

        mock_message.answer.assert_called_once()

    @pytest.mark.anyio
    async def test_account_no_user(self, mock_message, mock_T):
        """Test /account for unregistered user."""
        await cmd_account(mock_message, mock_T, None)

        mock_message.answer.assert_called_once_with("Account not found")


# ---------------------------------------------------------------------------
# Keyboard Tests
# ---------------------------------------------------------------------------

class TestKeyboards:
    """Tests for keyboard builders."""

    @pytest.mark.anyio
    async def test_main_menu_customer(self, mock_T):
        """Test main menu keyboard for customer."""
        kb = await build_main_menu(mock_T, user=None, is_admin=False)

        assert kb is not None
        # Should have buttons for Services, Account, Support, Language, Help
        # Not admin/stats

    @pytest.mark.anyio
    async def test_main_menu_admin(self, mock_T, mock_admin_user):
        """Test main menu keyboard for admin."""
        kb = await build_main_menu(mock_T, user=mock_admin_user)

        assert kb is not None
        # Should include admin and stats buttons

    @pytest.mark.anyio
    async def test_language_selector(self, mock_T):
        """Test language selector keyboard."""
        kb = await build_language_selector(mock_T)

        assert kb is not None
        # Should have buttons for each locale

    @pytest.mark.anyio
    async def test_supported_locales(self):
        """Test supported locales dictionary."""
        assert "en" in SUPPORTED_LOCALES
        assert "fa" in SUPPORTED_LOCALES
        assert len(SUPPORTED_LOCALES) >= 2

    @pytest.mark.anyio
    async def test_language_confirmation(self, mock_T):
        """Test language confirmation keyboard."""
        kb = await build_language_confirmation(mock_T, "fa")

        assert kb is not None
        # Should have a "Done" button with callback data