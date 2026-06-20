"""
BlueHub I18n Unit Tests
=======================
Tests for I18nEngine, translation loading, nested keys,
variable substitution, English fallback, language detection,
and Redis caching.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.i18n.engine import (
    I18nEngine,
    _get_nested_value,
    _load_translation_file,
    _substitute_variables,
    i18n_engine,
)

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_en_translations() -> dict:
    """Sample English translations for testing."""
    return {
        "app": {
            "name": "BlueHub",
            "welcome": "Welcome to BlueHub",
        },
        "auth": {
            "login": "Login",
            "logout": "Logout",
            "errors": {
                "invalid_credentials": "Invalid username or password",
                "session_expired": "Your session has expired",
            },
        },
        "user": {
            "profile": "User Profile",
            "wallet_credited": "Your wallet has been credited with {amount} {currency}",
        },
        "errors": {
            "not_found": "Resource not found",
            "module_disabled": "Module {module_name} is disabled",
        },
        "common": {
            "save": "Save",
            "cancel": "Cancel",
            "delete": "Delete",
            "confirm": "Are you sure?",
        },
    }


@pytest.fixture()
def sample_fa_translations() -> dict:
    """Sample Persian translations for testing."""
    return {
        "app": {
            "name": "بلوهاب",
            "welcome": "به بلوهاب خوش آمدید",
        },
        "auth": {
            "login": "ورود",
            "logout": "خروج",
            "errors": {
                "invalid_credentials": "نام کاربری یا رمز عبور اشتباه است",
            },
        },
        "errors": {
            "module_disabled": "ماژول {module_name} غیرفعال است",
        },
    }


@pytest.fixture()
def temp_locale_dir(sample_en_translations, sample_fa_translations):
    """Create a temporary directory with test translation files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write en.json
        en_path = Path(tmpdir) / "en.json"
        with open(en_path, "w", encoding="utf-8") as f:
            json.dump(sample_en_translations, f, ensure_ascii=False)

        # Write fa.json
        fa_path = Path(tmpdir) / "fa.json"
        with open(fa_path, "w", encoding="utf-8") as f:
            json.dump(sample_fa_translations, f, ensure_ascii=False)

        yield tmpdir


# ── _load_translation_file ────────────────────────────────────────────────


class TestLoadTranslationFile:
    """Tests for the _load_translation_file function."""

    def test_load_existing_file(self, temp_locale_dir):
        """Should load an existing translation file successfully."""
        with patch("core.i18n.engine.settings") as mock_settings:
            mock_settings.LOCALES_PATH = temp_locale_dir
            data = _load_translation_file("en")
            assert data["app"]["name"] == "BlueHub"
            assert data["auth"]["login"] == "Login"

    def test_load_non_existent_file(self, temp_locale_dir):
        """Should return empty dict for non-existent file."""
        with patch("core.i18n.engine.settings") as mock_settings:
            mock_settings.LOCALES_PATH = temp_locale_dir
            data = _load_translation_file("de")
            assert data == {}

    def test_load_invalid_json(self, temp_locale_dir):
        """Should return empty dict for invalid JSON file."""
        # Create an invalid JSON file
        invalid_path = Path(temp_locale_dir) / "invalid.json"
        with open(invalid_path, "w", encoding="utf-8") as f:
            f.write("{invalid json content")

        with patch("core.i18n.engine.settings") as mock_settings:
            mock_settings.LOCALES_PATH = temp_locale_dir
            data = _load_translation_file("invalid")
            assert data == {}


# ── _get_nested_value ─────────────────────────────────────────────────────


class TestGetNestedValue:
    """Tests for the _get_nested_value function."""

    def test_simple_key(self, sample_en_translations):
        """Should retrieve a top-level string value."""
        result = _get_nested_value(sample_en_translations, "app")
        assert result is None  # 'app' is a dict, not a string

    def test_nested_key_string(self, sample_en_translations):
        """Should retrieve a nested string value using dot notation."""
        result = _get_nested_value(sample_en_translations, "app.name")
        assert result == "BlueHub"

    def test_deeply_nested_key(self, sample_en_translations):
        """Should retrieve a deeply nested string value."""
        result = _get_nested_value(sample_en_translations, "auth.errors.invalid_credentials")
        assert result == "Invalid username or password"

    def test_missing_key(self, sample_en_translations):
        """Should return None for a missing key."""
        result = _get_nested_value(sample_en_translations, "nonexistent.key")
        assert result is None

    def test_partial_missing_key(self, sample_en_translations):
        """Should return None when part of the path is missing."""
        result = _get_nested_value(sample_en_translations, "auth.nonexistent.key")
        assert result is None

    def test_non_dict_intermediate(self, sample_en_translations):
        """Should return None when intermediate value is not a dict."""
        result = _get_nested_value(sample_en_translations, "app.name.nested")
        assert result is None

    def test_empty_key(self, sample_en_translations):
        """Should handle empty key gracefully."""
        result = _get_nested_value(sample_en_translations, "")
        assert result is None

    def test_none_data(self):
        """Should handle None data gracefully."""
        result = _get_nested_value(None, "some.key")
        assert result is None


# ── _substitute_variables ─────────────────────────────────────────────────


class TestSubstituteVariables:
    """Tests for the _substitute_variables function."""

    def test_no_variables(self):
        """Should return the message unchanged when no variables."""
        result = _substitute_variables("Hello, World!")
        assert result == "Hello, World!"

    def test_single_variable(self):
        """Should substitute a single variable."""
        result = _substitute_variables("Hello, {name}!", name="Ali")
        assert result == "Hello, Ali!"

    def test_multiple_variables(self):
        """Should substitute multiple variables."""
        result = _substitute_variables(
            "{amount} {currency} credited",
            amount="100,000",
            currency="Toman",
        )
        assert result == "100,000 Toman credited"

    def test_missing_variable(self):
        """Should keep the placeholder when variable is not provided."""
        result = _substitute_variables("Hello, {name}!")
        assert result == "Hello, {name}!"

    def test_same_variable_multiple_times(self):
        """Should substitute the same variable appearing multiple times."""
        result = _substitute_variables("{x} + {x} = {y}", x="1", y="2")
        assert result == "1 + 1 = 2"

    def test_empty_message(self):
        """Should handle empty message."""
        result = _substitute_variables("")
        assert result == ""

    def test_no_placeholders_with_kwargs(self):
        """Should return message unchanged when kwargs provided but no placeholders."""
        result = _substitute_variables("Static message", extra="value")
        assert result == "Static message"


# ── I18nEngine ────────────────────────────────────────────────────────────


class TestI18nEngine:
    """Tests for the I18nEngine class."""

    @pytest.fixture()
    def engine(self, temp_locale_dir):
        """Create I18nEngine with test locale directory."""
        with patch("core.i18n.engine.settings") as mock_settings:
            mock_settings.LOCALES_PATH = temp_locale_dir
            mock_settings.SUPPORTED_LOCALES = ["en", "fa", "ar"]
            mock_settings.DEFAULT_LOCALE = "en"
            engine = I18nEngine(default_locale="en")
            yield engine

    @pytest.mark.asyncio()
    async def test_get_existing_key(self, engine):
        """Should return the correct translation for an existing key."""
        result = await engine.get("app.name", locale="en")
        assert result == "BlueHub"

    @pytest.mark.asyncio()
    async def test_get_nested_key(self, engine):
        """Should return translation for deeply nested keys."""
        result = await engine.get("auth.errors.invalid_credentials", locale="en")
        assert result == "Invalid username or password"

    @pytest.mark.asyncio()
    async def test_get_missing_key_returns_default(self, engine):
        """Should return default value when key is missing."""
        result = await engine.get("nonexistent.key", locale="en", default="Fallback")
        assert result == "Fallback"

    @pytest.mark.asyncio()
    async def test_get_missing_key_returns_key(self, engine):
        """Should return the key itself when no default provided."""
        result = await engine.get("nonexistent.key", locale="en")
        assert result == "nonexistent.key"

    @pytest.mark.asyncio()
    async def test_get_with_variable_substitution(self, engine):
        """Should substitute variables in the translation."""
        result = await engine.get(
            "user.wallet_credited",
            locale="en",
            amount="500,000",
            currency="Toman",
        )
        assert result == "Your wallet has been credited with 500,000 Toman"

    @pytest.mark.asyncio()
    async def test_english_fallback(self, engine):
        """Should fall back to English when translation missing in target locale."""
        # 'errors.not_found' is only in en.json, not fa.json
        result = await engine.get("errors.not_found", locale="fa")
        assert result == "Resource not found"

    @pytest.mark.asyncio()
    async def test_persian_translation(self, engine):
        """Should return Persian translation when available."""
        result = await engine.get("app.name", locale="fa")
        assert result == "بلوهاب"

    @pytest.mark.asyncio()
    async def test_persian_with_variable(self, engine):
        """Should substitute variables in Persian translations."""
        result = await engine.get(
            "errors.module_disabled",
            locale="fa",
            module_name="VPN",
        )
        assert result == "ماژول VPN غیرفعال است"

    @pytest.mark.asyncio()
    async def test_get_batch(self, engine):
        """Should return multiple translations in batch."""
        keys = ["app.name", "app.welcome", "common.save"]
        results = await engine.get_batch(keys, locale="en")

        assert results["app.name"] == "BlueHub"
        assert results["app.welcome"] == "Welcome to BlueHub"
        assert results["common.save"] == "Save"

    @pytest.mark.asyncio()
    async def test_get_batch_with_missing_key(self, engine):
        """Should handle missing keys in batch."""
        keys = ["app.name", "nonexistent.key"]
        results = await engine.get_batch(keys, locale="en")

        assert results["app.name"] == "BlueHub"
        assert results["nonexistent.key"] == "nonexistent.key"

    @pytest.mark.asyncio()
    async def test_reload_locale(self, engine):
        """Should reload translations after reload_locale."""
        # First load
        result1 = await engine.get("app.name", locale="en")
        assert result1 == "BlueHub"

        # Reload
        await engine.reload_locale("en")

        # Should still work after reload
        result2 = await engine.get("app.name", locale="en")
        assert result2 == "BlueHub"

    @pytest.mark.asyncio()
    async def test_default_locale(self, engine):
        """Should use default locale when none specified."""
        result = await engine.get("app.name")
        assert result == "BlueHub"

    def test_detect_language_user_preferred(self, engine):
        """Should prefer user's saved language."""
        result = engine.detect_language(
            accept_language="ar,en;q=0.8",
            user_preferred="fa",
        )
        assert result == "fa"

    def test_detect_language_accept_header(self, engine):
        """Should use Accept-Language when no user preference."""
        result = engine.detect_language(
            accept_language="fa-IR,fa;q=0.9,en;q=0.8",
            user_preferred=None,
        )
        assert result == "fa"

    def test_detect_language_default(self, engine):
        """Should use default locale when nothing else matches."""
        result = engine.detect_language(
            accept_language=None,
            user_preferred=None,
        )
        assert result == "en"

    def test_detect_language_unsupported_user_pref(self, engine):
        """Should ignore unsupported user language."""
        result = engine.detect_language(
            accept_language="en;q=0.8",
            user_preferred="de",
        )
        assert result == "en"

    def test_detect_language_quality_sorting(self, engine):
        """Should respect quality values in Accept-Language."""
        result = engine.detect_language(
            accept_language="ar;q=0.5,fa;q=0.9,en;q=0.8",
            user_preferred=None,
        )
        assert result == "fa"

    def test_detect_language_first_match(self, engine):
        """Should return first supported language from header."""
        result = engine.detect_language(
            accept_language="de;q=0.9,fr;q=0.8",
            user_preferred=None,
        )
        assert result == "en"  # defaults to en since de/fr not in SUPPORTED_LOCALES


# ── Redis Caching ─────────────────────────────────────────────────────────


class TestI18nEngineRedisCaching:
    """Tests for Redis caching in I18nEngine."""

    @pytest.fixture()
    def engine(self, temp_locale_dir):
        """Create engine with test locales."""
        with patch("core.i18n.engine.settings") as mock_settings:
            mock_settings.LOCALES_PATH = temp_locale_dir
            mock_settings.SUPPORTED_LOCALES = ["en", "fa"]
            mock_settings.DEFAULT_LOCALE = "en"
            engine = I18nEngine(default_locale="en", cache_ttl=3600)
            yield engine

    @pytest.mark.asyncio()
    async def test_redis_cache_hit(self, engine, sample_en_translations):
        """Should use cached data from Redis when available."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(sample_en_translations)

        with patch("core.i18n.engine._get_redis_client", return_value=mock_redis):
            result = await engine.get("app.name", locale="en")
            assert result == "BlueHub"
            mock_redis.get.assert_called_once_with("i18n:en")

    @pytest.mark.asyncio()
    async def test_redis_cache_miss_then_disk(self, engine, temp_locale_dir):
        """Should load from disk when Redis miss and cache to Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Cache miss

        with patch("core.i18n.engine._get_redis_client", return_value=mock_redis):
            with patch("core.i18n.engine.settings") as mock_settings:
                mock_settings.LOCALES_PATH = temp_locale_dir
                result = await engine.get("app.name", locale="en")
                assert result == "BlueHub"
                mock_redis.get.assert_called_once_with("i18n:en")
                mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio()
    async def test_redis_unavailable_fallback_to_memory(self, engine):
        """Should fall back to in-memory cache when Redis is unavailable."""
        with patch("core.i18n.engine._get_redis_client", return_value=None):
            # First load from disk
            result = await engine.get("app.name", locale="en")
            assert result == "BlueHub"

            # Second call should use in-memory cache
            result2 = await engine.get("app.welcome", locale="en")
            assert result2 == "Welcome to BlueHub"

    @pytest.mark.asyncio()
    async def test_redis_error_fallback(self, engine, sample_en_translations):
        """Should fall back gracefully on Redis error."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")

        with patch("core.i18n.engine._get_redis_client", return_value=mock_redis):
            # Should not raise, should fall back to disk
            result = await engine.get("app.name", locale="en")
            assert result == "BlueHub"

    @pytest.mark.asyncio()
    async def test_reload_clears_redis_cache(self, engine, sample_en_translations):
        """Should delete Redis cache on reload."""
        mock_redis = AsyncMock()

        with patch("core.i18n.engine._get_redis_client", return_value=mock_redis):
            await engine.reload_locale("en")
            mock_redis.delete.assert_called_once_with("i18n:en")


# ── Singleton Instance ────────────────────────────────────────────────────


class TestI18nSingleton:
    """Tests for the singleton i18n_engine instance."""

    def test_singleton_is_engine_instance(self):
        """Should be an instance of I18nEngine."""
        assert isinstance(i18n_engine, I18nEngine)

    def test_singleton_default_locale(self):
        """Should have default_locale set from settings."""
        assert i18n_engine.default_locale in ["en", "fa"]
        assert hasattr(i18n_engine, "default_locale")
