"""
Central Logging Client for Wind Turbine Earthwork Calculator V2

Opt-in telemetry client that forwards a small set of usage events to the
central logging API at log.broetzens.de. The module is strictly fail-safe and
non-blocking: every send happens on a daemon thread, all errors are swallowed,
and if no API key file is present, ``log_event`` is a no-op.

Opt-in is file-based: telemetry is active if and only if a file named
``log.config`` exists next to the plugin's ``__init__.py`` and contains a real
API key (not empty, not the placeholder ``REPLACE_WITH_YOUR_API_KEY``).

Payloads NEVER contain PII: no file paths, user names, hostnames, IP
addresses, coordinates, stack traces, or error messages.
"""

import threading
import uuid
from pathlib import Path
from typing import Optional

import requests

try:  # pragma: no cover - QGIS not available in unit tests
    from qgis.core import Qgis, QgsMessageLog
    from qgis.PyQt.QtCore import QSettings
    _QGIS_AVAILABLE = True
except Exception:  # pragma: no cover
    Qgis = None  # type: ignore[assignment]
    QgsMessageLog = None  # type: ignore[assignment]
    QSettings = None  # type: ignore[assignment]
    _QGIS_AVAILABLE = False


TOOL_NAME = "wind-turbine-earthwork-calculator"
API_ENDPOINT = "https://log.broetzens.de/api/log"
HTTP_TIMEOUT_SECONDS = 5
PLACEHOLDER_API_KEY = "REPLACE_WITH_YOUR_API_KEY"
LOG_CONFIG_FILENAME = "log.config"
INSTALLATION_ID_SETTINGS_KEY = "wind-turbine-earthwork-calculator/installation_id"
_MESSAGE_LOG_TAG = "WindTurbine Telemetry"


def _plugin_root() -> Path:
    """Return the plugin root directory (where ``__init__.py`` lives)."""
    return Path(__file__).resolve().parent.parent


def _log_config_path() -> Path:
    """Return the expected path of the ``log.config`` file."""
    return _plugin_root() / LOG_CONFIG_FILENAME


def _metadata_path() -> Path:
    """Return the expected path of the plugin's ``metadata.txt`` file."""
    return _plugin_root() / "metadata.txt"


def _read_api_key() -> Optional[str]:
    """Read the API key from ``log.config`` or return ``None``.

    Returns ``None`` if the file does not exist, is empty, or still contains
    the placeholder. Whitespace and newlines are stripped.
    """
    path = _log_config_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None

    key = raw.strip()
    if not key:
        return None
    if key == PLACEHOLDER_API_KEY:
        return None
    return key


def _read_tool_version() -> str:
    """Parse ``version=`` from ``metadata.txt`` or return ``"unknown"``."""
    path = _metadata_path()
    try:
        content = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return "unknown"

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("version"):
            _, _, value = stripped.partition("=")
            value = value.strip()
            if value:
                return value
    return "unknown"


def _qgis_log(message: str, warning: bool = False) -> None:
    """Write a message to the QGIS message log if QGIS is available."""
    if not _QGIS_AVAILABLE or QgsMessageLog is None or Qgis is None:
        return
    try:
        level = Qgis.Warning if warning else Qgis.Info
        QgsMessageLog.logMessage(message, _MESSAGE_LOG_TAG, level=level)
    except Exception:
        # Never let logging itself raise.
        pass


def _load_or_create_instance_id() -> str:
    """Return a stable anonymous installation UUID, persisted in ``QSettings``.

    Falls back to a fresh in-memory UUID if ``QSettings`` is unavailable
    (e.g. in unit tests without QGIS).
    """
    if not _QGIS_AVAILABLE or QSettings is None:
        return str(uuid.uuid4())
    try:
        settings = QSettings()
        stored = settings.value(INSTALLATION_ID_SETTINGS_KEY, "")
        if isinstance(stored, str) and stored:
            return stored
        new_id = str(uuid.uuid4())
        settings.setValue(INSTALLATION_ID_SETTINGS_KEY, new_id)
        return new_id
    except Exception:
        return str(uuid.uuid4())


class _TelemetryState:
    """Cached, lazily-initialised telemetry configuration."""

    def __init__(self) -> None:
        self._initialised = False
        self._lock = threading.Lock()
        self.api_key: Optional[str] = None
        self.tool_version: str = "unknown"
        self.instance_id: str = ""

    def ensure_initialised(self) -> None:
        """Initialise cached values exactly once."""
        if self._initialised:
            return
        with self._lock:
            if self._initialised:
                return
            self.api_key = _read_api_key()
            self.tool_version = _read_tool_version()
            self.instance_id = _load_or_create_instance_id()
            if self.api_key:
                _qgis_log(
                    "Central telemetry active (events forwarded to "
                    "log.broetzens.de)."
                )
            else:
                _qgis_log(
                    "Central telemetry inactive (no valid log.config)."
                )
            self._initialised = True

    def reset(self) -> None:
        """Reset cached state. Intended for use in tests only."""
        with self._lock:
            self._initialised = False
            self.api_key = None
            self.tool_version = "unknown"
            self.instance_id = ""


_state = _TelemetryState()


def _post_event(
    api_key: str,
    tool_version: str,
    instance_id: str,
    event: str,
    payload: Optional[dict],
) -> None:
    """Send a single event to the API, swallowing all errors."""
    body = {
        "tool": TOOL_NAME,
        "tool_version": tool_version,
        "instance": instance_id,
        "event": event,
    }
    if payload is not None:
        body["payload"] = payload

    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
    }

    try:
        requests.post(
            API_ENDPOINT,
            json=body,
            headers=headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 - strictly fail-safe
        # Deliberately swallow all exceptions; telemetry must never raise.
        _qgis_log(
            "Telemetry send failed: {0}".format(type(exc).__name__),
            warning=True,
        )


def log_event(event: str, payload: Optional[dict] = None) -> None:
    """Send a telemetry event asynchronously.

    This is a strict no-op if telemetry is not opted-in via ``log.config``.
    All network work happens on a daemon thread, so this function never
    blocks and never raises.

    Args:
        event: Event name (e.g. ``"calculation_started"``).
        payload: Optional JSON-serialisable dict with non-PII event fields.
    """
    try:
        _state.ensure_initialised()
        api_key = _state.api_key
        if not api_key:
            return
        thread = threading.Thread(
            target=_post_event,
            args=(
                api_key,
                _state.tool_version,
                _state.instance_id,
                event,
                payload,
            ),
            daemon=True,
        )
        thread.start()
    except Exception as exc:  # noqa: BLE001 - strictly fail-safe
        _qgis_log(
            "Telemetry dispatch failed: {0}".format(type(exc).__name__),
            warning=True,
        )
