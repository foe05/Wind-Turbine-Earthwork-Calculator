"""
Internationalization utilities for Wind Turbine Earthwork Calculator V2

Provides bilingual message support (German/English) with QGIS locale detection.
"""

import os
from typing import Optional, Dict, Any


# Module-level current language setting
_current_language: str = 'en'


def detect_qgis_locale() -> str:
    """
    Detect the current QGIS locale setting.

    Returns:
        str: Language code ('de' or 'en'). Defaults to 'en' if detection fails.
    """
    try:
        from qgis.core import QgsApplication

        # Get QGIS locale
        qgis_locale = QgsApplication.instance().locale()

        # Extract language code (first 2 characters)
        # e.g., 'de_DE' -> 'de', 'en_US' -> 'en'
        lang_code = qgis_locale[:2].lower()

        # Support only German and English
        if lang_code in ['de', 'en']:
            return lang_code
        else:
            # Default to English for unsupported locales
            return 'en'

    except Exception:
        # If QGIS is not available or detection fails, default to English
        return 'en'


def set_language(lang: str) -> None:
    """
    Manually set the language for error messages.

    Args:
        lang (str): Language code ('de' for German, 'en' for English)

    Raises:
        ValueError: If language code is not supported
    """
    global _current_language

    lang = lang.lower()

    if lang not in ['de', 'en']:
        raise ValueError(f"Unsupported language: {lang}. Use 'de' or 'en'.")

    _current_language = lang


def get_language() -> str:
    """
    Get the current language setting.

    Returns:
        str: Current language code ('de' or 'en')
    """
    return _current_language


def get_message(key: str, messages: Dict[str, Dict[str, str]], **params: Any) -> str:
    """
    Get a translated message by key with optional parameter substitution.

    Args:
        key (str): Message key to retrieve
        messages (dict): Dictionary of messages with structure:
                        {'key': {'de': '...', 'en': '...'}, ...}
        **params: Optional parameters for string formatting

    Returns:
        str: Translated message with parameters substituted

    Raises:
        KeyError: If message key is not found
    """
    if key not in messages:
        raise KeyError(f"Message key not found: {key}")

    message_dict = messages[key]
    lang = get_language()

    # Get message in current language, fallback to English
    if lang in message_dict:
        message = message_dict[lang]
    elif 'en' in message_dict:
        message = message_dict['en']
    else:
        raise KeyError(f"No translation found for key: {key}")

    # Substitute parameters if provided
    if params:
        try:
            message = message.format(**params)
        except KeyError as e:
            # If parameter is missing, return unformatted message
            # This prevents crashes due to missing parameters
            pass

    return message


def auto_detect_language() -> None:
    """
    Automatically detect and set language from QGIS locale.

    This function should be called during plugin initialization.
    """
    global _current_language
    _current_language = detect_qgis_locale()


# Auto-detect language on module import
# This can be overridden by calling set_language() explicitly
try:
    auto_detect_language()
except Exception:
    # If auto-detection fails, keep default English
    _current_language = 'en'
