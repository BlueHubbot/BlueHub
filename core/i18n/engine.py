"""
BlueHub I18n Engine
====================
Internationalization engine supporting JSON translation files,
nested key navigation, variable substitution, Redis caching,
and runtime language detection.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)

# Cache for loaded translations: {locale: {key: value}}
_translations_cache: dict[str, dict[str, Any]] = {}
_redis_client = None

# Pattern for variable substitution: {variable_name}
_VARIABLE_PATTERN = re.compile(r"\{(\w+)\}")


def _get_redis_client():
    """Get Redis client for caching translations."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis

            _redis_client = aioredis.from_url(
                str(settings.REDIS_URL) if settings.REDIS_URL else "redis://localhost:6379/0",
                encoding="utf-8",
                decode_responses=True,
            )
        except ImportError:
            logger.warning("Redis not available, using in-memory cache only")
            _redis_client = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client


def _load_translation_file(locale: str) -> dict[str, Any]:
    """
    Load a translation JSON file from disk.

    Args:
        locale: Language code (e.g., 'en', 'fa')

    Returns:
        Dictionary of translation keys and values
    """
    base_path = Path(settings.LOCALES_PATH)
    file_path = base_path / f"{locale}.json"

    if not file_path.exists():
        logger.warning(f"Translation file not found: {file_path}")
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in translation file {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load translation file {file_path}: {e}")
        return {}


def _get_nested_value(data: dict[str, Any], key: str) -> str | None:
    """
    Navigate nested dictionary using dot notation.

    Args:
        data: Nested dictionary of translations
        key: Dot-separated key path (e.g., "errors.module_disabled")

    Returns:
        Translation string or None if not found
    """
    keys = key.split(".")
    current = data

    for k in keys:
        if isinstance(current, dict):
            if k in current:
                current = current[k]
            else:
                return None
        else:
            return None

    if isinstance(current, str):
        return current
    return None


def _substitute_variables(message: str, **kwargs: Any) -> str:
    """
    Replace {variable_name} placeholders with provided values.

    Args:
        message: Template string with {variable} placeholders
        **kwargs: Variable values to substitute

    Returns:
        Message with variables substituted
    """

    def replace_match(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in kwargs:
            return str(kwargs[var_name])
        # Keep the placeholder if variable not provided
        return match.group(0)

    return _VARIABLE_PATTERN.sub(replace_match, message)


class I18nEngine:
    """
    Internationalization engine with Redis caching and language detection.

    Supports:
    - JSON translation files per locale
    - Nested key navigation (dot notation)
    - Variable substitution ({variable_name})
    - Fallback to English (en) when translation missing
    - Redis cache with 1-hour TTL
    - In-memory cache fallback when Redis unavailable

    Usage:
        i18n = I18nEngine()
        msg = await i18n.get("errors.module_disabled", locale="fa", module_name="VPN")
        # Returns: "ماژول VPN غیرفعال است" (or English fallback)
    """

    def __init__(self, default_locale: str = "en", cache_ttl: int = 3600):
        """
        Initialize I18nEngine.

        Args:
            default_locale: Default language code (default: 'en')
            cache_ttl: Redis cache TTL in seconds (default: 3600 = 1 hour)
        """
        self.default_locale = default_locale
        self.cache_ttl = cache_ttl
        self._locale_data: dict[str, dict[str, Any]] = {}
        self._loaded: set[str] = set()

    async def _load_from_redis(self, locale: str) -> dict[str, Any] | None:
        """Try to load translations from Redis cache."""
        client = _get_redis_client()
        if client is None:
            return None

        try:
            cache_key = f"i18n:{locale}"
            cached = await client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Redis cache read failed for {locale}: {e}")

        return None

    async def _save_to_redis(self, locale: str, data: dict[str, Any]) -> None:
        """Save translations to Redis cache."""
        client = _get_redis_client()
        if client is None:
            return

        try:
            cache_key = f"i18n:{locale}"
            await client.setex(cache_key, self.cache_ttl, json.dumps(data))
        except Exception as e:
            logger.debug(f"Redis cache write failed for {locale}: {e}")

    async def _ensure_loaded(self, locale: str) -> dict[str, Any]:
        """Ensure translations for a locale are loaded (from Redis or disk)."""
        if locale in self._loaded:
            return self._locale_data.get(locale, {})

        # Try Redis first
        redis_data = await self._load_from_redis(locale)
        if redis_data is not None:
            self._locale_data[locale] = redis_data
            self._loaded.add(locale)
            return redis_data

        # Load from disk
        file_data = _load_translation_file(locale)
        if file_data:
            self._locale_data[locale] = file_data
            self._loaded.add(locale)
            # Cache in Redis asynchronously (fire and forget)
            await self._save_to_redis(locale, file_data)
            return file_data

        # Empty fallback
        self._locale_data[locale] = {}
        self._loaded.add(locale)
        return {}

    async def get(
        self,
        key: str,
        locale: str | None = None,
        default: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Get a translated message by key.

        Args:
            key: Translation key (supports dot notation, e.g., "errors.module_disabled")
            locale: Target locale (defaults to engine's default_locale)
            default: Fallback message if translation not found
            **kwargs: Variables for substitution (e.g., module_name="VPN")

        Returns:
            Translated message string

        Examples:
            await i18n.get("welcome", locale="fa")
            await i18n.get("errors.module_disabled", locale="fa", module_name="VPN")
            await i18n.get("user.not_found", default="User not found")
        """
        locale = locale or self.default_locale

        # Try requested locale
        data = await self._ensure_loaded(locale)
        message = _get_nested_value(data, key)

        # Fallback to English if not found and locale is not English
        if message is None and locale != "en":
            en_data = await self._ensure_loaded("en")
            message = _get_nested_value(en_data, key)

        # Use default if still not found
        if message is None:
            return default or key

        # Substitute variables
        return _substitute_variables(message, **kwargs)

    async def get_batch(
        self,
        keys: list[str],
        locale: str | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        """
        Get multiple translated messages in a single call.

        Args:
            keys: List of translation keys
            locale: Target locale
            **kwargs: Variables for substitution

        Returns:
            Dictionary mapping keys to translated messages
        """
        result = {}
        for key in keys:
            result[key] = await self.get(key, locale=locale, **kwargs)
        return result

    async def reload_locale(self, locale: str) -> None:
        """
        Force reload translations for a locale (clear cache and reload).

        Args:
            locale: Language code to reload
        """
        # Clear in-memory cache
        self._loaded.discard(locale)
        if locale in self._locale_data:
            del self._locale_data[locale]

        # Clear Redis cache
        client = _get_redis_client()
        if client:
            try:
                cache_key = f"i18n:{locale}"
                await client.delete(cache_key)
            except Exception:
                pass

        # Reload
        await self._ensure_loaded(locale)

    def detect_language(
        self,
        accept_language: str | None = None,
        user_preferred: str | None = None,
    ) -> str:
        """
        Detect the best language to use based on priority order:
        1. User's saved preference
        2. Accept-Language header
        3. Default locale

        Args:
            accept_language: Value of Accept-Language HTTP header
            user_preferred: User's stored language preference

        Returns:
            Detected language code
        """
        # 1. User's saved preference
        if user_preferred and user_preferred in settings.SUPPORTED_LOCALES:
            return user_preferred

        # 2. Accept-Language header
        if accept_language:
            # Parse Accept-Language header (e.g., "fa-IR,fa;q=0.9,en;q=0.8")
            languages = []
            for part in accept_language.split(","):
                part = part.strip()
                if ";" in part:
                    lang, q = part.split(";", 1)
                    q_value = 1.0
                    if "q=" in q:
                        try:
                            q_value = float(q.split("q=")[1])
                        except ValueError:
                            q_value = 1.0
                    languages.append((lang.split("-")[0].strip(), q_value))
                else:
                    languages.append((part.split("-")[0].strip(), 1.0))

            # Sort by quality value (descending)
            languages.sort(key=lambda x: x[1], reverse=True)

            for lang, _ in languages:
                if lang in settings.SUPPORTED_LOCALES:
                    return lang

        # 3. Default locale
        return self.default_locale


# Singleton instance
i18n_engine = I18nEngine(
    default_locale=settings.DEFAULT_LOCALE,
)

__all__ = [
    "I18nEngine",
    "i18n_engine",
    "_load_translation_file",
    "_get_nested_value",
    "_substitute_variables",
]
