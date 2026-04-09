"""
Tests for the central telemetry client (``utils.central_logging``).

These tests exercise the opt-in gating, the request format, and the
fail-safe behaviour. No real network calls are made; ``requests.post`` is
patched in every test and waited on synchronously by joining the dispatch
thread.
"""

import sys
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock


# ---------------------------------------------------------------------------
# QGIS / PyQt stubs so the module can be imported outside QGIS.
# ---------------------------------------------------------------------------

def _install_qgis_stubs() -> None:
    """Install minimal ``qgis`` and ``qgis.PyQt`` stubs if QGIS is absent."""
    if "qgis" in sys.modules:
        return

    qgis_module = types.ModuleType("qgis")
    qgis_core = types.ModuleType("qgis.core")
    qgis_pyqt = types.ModuleType("qgis.PyQt")
    qgis_qtcore = types.ModuleType("qgis.PyQt.QtCore")

    class _Qgis:
        Info = 0
        Warning = 1

    class _QgsMessageLog:
        @staticmethod
        def logMessage(*_args, **_kwargs):
            return None

    class _QSettings:
        _store = {}

        def value(self, key, default=""):
            return _QSettings._store.get(key, default)

        def setValue(self, key, value):
            _QSettings._store[key] = value

    qgis_core.Qgis = _Qgis
    qgis_core.QgsMessageLog = _QgsMessageLog
    qgis_qtcore.QSettings = _QSettings
    qgis_pyqt.QtCore = qgis_qtcore
    qgis_module.core = qgis_core
    qgis_module.PyQt = qgis_pyqt

    sys.modules["qgis"] = qgis_module
    sys.modules["qgis.core"] = qgis_core
    sys.modules["qgis.PyQt"] = qgis_pyqt
    sys.modules["qgis.PyQt.QtCore"] = qgis_qtcore


_install_qgis_stubs()

# Make the plugin package importable when the tests are executed directly.
_PLUGIN_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PLUGIN_DIR.parent
for _path in (_REPO_ROOT, _PLUGIN_DIR.parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from windturbine_earthwork_calculator_v2.utils import central_logging  # noqa: E402


def _join_background_threads(timeout: float = 2.0) -> None:
    """Wait for any daemon telemetry threads to finish their POST call."""
    deadline = time.time() + timeout
    for thread in list(threading.enumerate()):
        if thread is threading.current_thread():
            continue
        if not thread.daemon:
            continue
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        thread.join(timeout=remaining)


class CentralLoggingTestCase(unittest.TestCase):
    """Shared setup that isolates ``log.config`` and cached state per test."""

    def setUp(self) -> None:
        self._tmp_config = _PLUGIN_DIR / "log.config"
        self._backup: bytes | None = None
        if self._tmp_config.exists():
            self._backup = self._tmp_config.read_bytes()
            self._tmp_config.unlink()
        central_logging._state.reset()

    def tearDown(self) -> None:
        if self._tmp_config.exists():
            self._tmp_config.unlink()
        if self._backup is not None:
            self._tmp_config.write_bytes(self._backup)
        central_logging._state.reset()

    def _write_config(self, content: str) -> None:
        self._tmp_config.write_text(content, encoding="utf-8")


class LogConfigGatingTests(CentralLoggingTestCase):
    """Telemetry must be a strict no-op when opt-in is missing."""

    def test_missing_config_is_noop(self) -> None:
        self.assertFalse(self._tmp_config.exists())
        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post"
        ) as post:
            central_logging.log_event("calculation_started", {"a": 1})
            _join_background_threads()
            post.assert_not_called()

    def test_placeholder_config_is_noop(self) -> None:
        self._write_config("REPLACE_WITH_YOUR_API_KEY")
        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post"
        ) as post:
            central_logging.log_event("calculation_started")
            _join_background_threads()
            post.assert_not_called()

    def test_empty_config_is_noop(self) -> None:
        self._write_config("   \n\n")
        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post"
        ) as post:
            central_logging.log_event("calculation_started")
            _join_background_threads()
            post.assert_not_called()


class ValidKeyDispatchTests(CentralLoggingTestCase):
    """When a key is present, we send exactly one POST with the right shape."""

    def setUp(self) -> None:
        super().setUp()
        self._write_config("secret-api-key\n")

    def test_posts_once_with_expected_headers_and_body(self) -> None:
        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post"
        ) as post:
            post.return_value = mock.Mock(status_code=201)

            central_logging.log_event(
                "calculation_started",
                {"num_turbines": 1, "dem_source_type": "hoehendaten_api"},
            )
            _join_background_threads()

            self.assertEqual(post.call_count, 1)
            args, kwargs = post.call_args
            self.assertEqual(args[0], central_logging.API_ENDPOINT)

            headers = kwargs["headers"]
            self.assertEqual(headers["X-Api-Key"], "secret-api-key")
            self.assertEqual(headers["Content-Type"], "application/json")

            self.assertEqual(kwargs["timeout"], central_logging.HTTP_TIMEOUT_SECONDS)

            body = kwargs["json"]
            self.assertEqual(body["tool"], "wind-turbine-earthwork-calculator")
            self.assertEqual(body["event"], "calculation_started")
            self.assertIn("instance", body)
            self.assertTrue(body["instance"])
            self.assertEqual(
                body["payload"],
                {"num_turbines": 1, "dem_source_type": "hoehendaten_api"},
            )
            self.assertIn("tool_version", body)

    def test_instance_id_stable_across_calls(self) -> None:
        captured_instances = []

        def _capture(*_args, **kwargs):
            captured_instances.append(kwargs["json"]["instance"])
            return mock.Mock(status_code=201)

        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post",
            side_effect=_capture,
        ):
            central_logging.log_event("calculation_started")
            _join_background_threads()
            central_logging.log_event("calculation_completed")
            _join_background_threads()
            central_logging.log_event("report_generated")
            _join_background_threads()

        self.assertEqual(len(captured_instances), 3)
        self.assertEqual(len(set(captured_instances)), 1)


class FailSafeTests(CentralLoggingTestCase):
    """Telemetry must never raise, even when the server or network misbehaves."""

    def setUp(self) -> None:
        super().setUp()
        self._write_config("secret-api-key")

    def test_http_500_does_not_raise(self) -> None:
        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post"
        ) as post:
            post.return_value = mock.Mock(status_code=500)
            try:
                central_logging.log_event("calculation_failed", {"error_class": "X"})
            except Exception as exc:  # pragma: no cover - defensive
                self.fail(f"log_event raised on HTTP 500: {exc!r}")
            _join_background_threads()
            post.assert_called_once()

    def test_connection_timeout_does_not_raise(self) -> None:
        import requests as _requests

        def _raise_timeout(*_args, **_kwargs):
            raise _requests.exceptions.ConnectTimeout("boom")

        with mock.patch(
            "windturbine_earthwork_calculator_v2.utils.central_logging"
            ".requests.post",
            side_effect=_raise_timeout,
        ) as post:
            try:
                central_logging.log_event("calculation_started")
            except Exception as exc:  # pragma: no cover - defensive
                self.fail(f"log_event raised on timeout: {exc!r}")
            _join_background_threads()
            post.assert_called_once()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
