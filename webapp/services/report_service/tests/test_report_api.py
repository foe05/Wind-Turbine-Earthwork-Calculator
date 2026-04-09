"""
Integration tests for Report API endpoints - Security Focus

These tests verify that the download_report endpoint properly validates
filenames and prevents path traversal attacks while allowing legitimate
report downloads.
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.main import app


class TestDownloadEndpointSecurity(unittest.TestCase):
    """Test suite for download_report endpoint security"""

    @classmethod
    def setUpClass(cls):
        """Set up test client once for all tests"""
        cls.client = TestClient(app)

    def setUp(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.reports_dir = Path(self.temp_dir) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid test report file
        self.valid_report_name = "report_test123.pdf"
        self.valid_report_path = self.reports_dir / self.valid_report_name
        self.valid_report_path.write_text("PDF content here")

        # Create a sensitive file outside reports directory
        self.sensitive_file = Path(self.temp_dir) / ".env"
        self.sensitive_file.write_text("DB_PASSWORD=secret123\nJWT_SECRET=supersecret")

        # Patch REPORTS_DIR to use our temp directory
        self.reports_dir_patch = patch(
            'app.api.report.REPORTS_DIR',
            self.reports_dir
        )
        self.reports_dir_patch.start()

    def tearDown(self):
        """Clean up temporary directory"""
        self.reports_dir_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_report_download(self):
        """Test that valid report files can be downloaded"""
        response = self.client.get(
            f"/report/download/test123/{self.valid_report_name}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"PDF content here")
        self.assertEqual(response.headers["content-type"], "application/pdf")

    def test_valid_html_report_download(self):
        """Test that valid HTML report files can be downloaded with correct media type"""
        # Create HTML report
        html_report_name = "report_test456.html"
        html_report_path = self.reports_dir / html_report_name
        html_report_path.write_text("<html><body>Test Report</body></html>")

        response = self.client.get(
            f"/report/download/test456/{html_report_name}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"<html><body>Test Report</body></html>")
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_path_traversal_unix_style(self):
        """Test that Unix-style path traversal attempts are blocked"""
        malicious_filenames = [
            "../.env",
            "../../.env",
            "../../../etc/passwd",
            "test/../../../.env",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                response = self.client.get(
                    f"/report/download/fake_id/{filename}"
                )

                self.assertEqual(
                    response.status_code, 400,
                    f"Expected 400 for {filename}, got {response.status_code}"
                )
                self.assertIn("Invalid filename", response.json()["detail"])

    def test_path_traversal_windows_style(self):
        """Test that Windows-style path traversal attempts are blocked"""
        malicious_filenames = [
            "..\\..\\windows\\system32",
            "..\\..\\..\\windows\\system32\\config",
            "test\\..\\..\\sensitive.txt",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                response = self.client.get(
                    f"/report/download/fake_id/{filename}"
                )

                self.assertEqual(
                    response.status_code, 400,
                    f"Expected 400 for {filename}, got {response.status_code}"
                )
                self.assertIn("Invalid filename", response.json()["detail"])

    def test_absolute_paths(self):
        """Test that absolute path attempts are blocked"""
        malicious_filenames = [
            "/etc/passwd",
            "/var/log/auth.log",
            "/root/.ssh/id_rsa",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                response = self.client.get(
                    f"/report/download/fake_id/{filename}"
                )

                self.assertEqual(
                    response.status_code, 400,
                    f"Expected 400 for {filename}, got {response.status_code}"
                )
                self.assertIn("Invalid filename", response.json()["detail"])

    def test_url_encoded_traversal(self):
        """Test that URL-encoded path traversal attempts are blocked"""
        malicious_filenames = [
            "%2e%2e/etc/passwd",
            "%2e%2e%2fetc%2fpasswd",
            "%2E%2E/secret.txt",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                response = self.client.get(
                    f"/report/download/fake_id/{filename}"
                )

                self.assertEqual(
                    response.status_code, 400,
                    f"Expected 400 for {filename}, got {response.status_code}"
                )
                self.assertIn("Invalid filename", response.json()["detail"])

    def test_null_byte_injection(self):
        """Test that null byte injection attempts are blocked"""
        # Note: URL encoding of null byte is %00
        malicious_filenames = [
            "report.pdf\x00.txt",
            "report\x00.pdf",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                response = self.client.get(
                    f"/report/download/fake_id/{filename}"
                )

                self.assertEqual(
                    response.status_code, 400,
                    f"Expected 400 for {filename}, got {response.status_code}"
                )
                self.assertIn("Invalid filename", response.json()["detail"])

    def test_nonexistent_file(self):
        """Test that non-existent files return 404"""
        response = self.client.get(
            "/report/download/fake_id/nonexistent_report.pdf"
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("Report not found", response.json()["detail"])

    def test_empty_filename(self):
        """Test that empty filenames are rejected"""
        response = self.client.get(
            "/report/download/fake_id/"
        )

        # This will return 404 because of routing, but that's acceptable
        # The important thing is it doesn't try to access any file
        self.assertIn(response.status_code, [404, 405])

    def test_mixed_attack_vectors(self):
        """Test combinations of multiple attack vectors"""
        malicious_filenames = [
            "../../../etc/passwd\x00.txt",
            "%2e%2e/../etc/passwd",
            "..\\../etc/passwd",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                response = self.client.get(
                    f"/report/download/fake_id/{filename}"
                )

                self.assertEqual(
                    response.status_code, 400,
                    f"Expected 400 for {filename}, got {response.status_code}"
                )
                self.assertIn("Invalid filename", response.json()["detail"])

    def test_cannot_access_parent_directory_files(self):
        """Test that files in parent directory cannot be accessed even if they exist"""
        # The sensitive file exists in parent directory
        self.assertTrue(self.sensitive_file.exists())

        # Try to access it via path traversal
        response = self.client.get(
            "/report/download/fake_id/../.env"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid filename", response.json()["detail"])

        # Verify the sensitive file was NOT accessed
        # (it should still have the same content)
        self.assertEqual(
            self.sensitive_file.read_text(),
            "DB_PASSWORD=secret123\nJWT_SECRET=supersecret"
        )

    def test_error_message_does_not_leak_paths(self):
        """Test that error messages don't leak internal path information"""
        response = self.client.get(
            "/report/download/fake_id/../../../etc/passwd"
        )

        self.assertEqual(response.status_code, 400)
        error_detail = response.json()["detail"]

        # Verify error message doesn't contain internal paths
        self.assertNotIn(self.temp_dir, error_detail)
        self.assertNotIn("/etc/passwd", error_detail)
        self.assertNotIn(str(self.reports_dir), error_detail)

        # Should be a generic security message
        self.assertIn("Invalid filename", error_detail)


class TestDownloadEndpointLogging(unittest.TestCase):
    """Test suite for security event logging"""

    @classmethod
    def setUpClass(cls):
        """Set up test client once for all tests"""
        cls.client = TestClient(app)

    def setUp(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.reports_dir = Path(self.temp_dir) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Patch REPORTS_DIR to use our temp directory
        self.reports_dir_patch = patch(
            'app.api.report.REPORTS_DIR',
            self.reports_dir
        )
        self.reports_dir_patch.start()

    def tearDown(self):
        """Clean up temporary directory"""
        self.reports_dir_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('app.api.report.logger')
    def test_security_logging_on_path_traversal_attempt(self, mock_logger):
        """Test that path traversal attempts are logged"""
        response = self.client.get(
            "/report/download/fake_id/../../../etc/passwd"
        )

        self.assertEqual(response.status_code, 400)

        # Verify security event was logged
        mock_logger.warning.assert_called()
        logged_message = str(mock_logger.warning.call_args)

        self.assertIn("Invalid filename", logged_message)

    @patch('app.api.report.logger')
    def test_valid_download_is_logged(self, mock_logger):
        """Test that successful downloads are logged"""
        # Create a valid report file
        valid_report_name = "report_test789.pdf"
        valid_report_path = self.reports_dir / valid_report_name
        valid_report_path.write_text("PDF content")

        response = self.client.get(
            f"/report/download/test789/{valid_report_name}"
        )

        self.assertEqual(response.status_code, 200)

        # Verify successful download was logged
        mock_logger.info.assert_called()
        logged_messages = [str(call) for call in mock_logger.info.call_args_list]
        logged_text = " ".join(logged_messages)

        self.assertIn("Downloading report", logged_text)


class TestDownloadEndpointIntegration(unittest.TestCase):
    """Integration tests for full download workflow"""

    @classmethod
    def setUpClass(cls):
        """Set up test client once for all tests"""
        cls.client = TestClient(app)

    def setUp(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.reports_dir = Path(self.temp_dir) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Patch REPORTS_DIR to use our temp directory
        self.reports_dir_patch = patch(
            'app.api.report.REPORTS_DIR',
            self.reports_dir
        )
        self.reports_dir_patch.start()

    def tearDown(self):
        """Clean up temporary directory"""
        self.reports_dir_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multiple_valid_downloads(self):
        """Test that multiple valid report files can be downloaded"""
        # Create multiple report files
        reports = [
            ("report_001.pdf", "Content 1"),
            ("report_002.pdf", "Content 2"),
            ("report_003.html", "<html>Report 3</html>"),
        ]

        for filename, content in reports:
            report_path = self.reports_dir / filename
            report_path.write_text(content)

        # Download each report and verify
        for filename, expected_content in reports:
            with self.subTest(filename=filename):
                report_id = filename.split('_')[1].split('.')[0]
                response = self.client.get(
                    f"/report/download/{report_id}/{filename}"
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.decode(), expected_content)

    def test_security_does_not_affect_valid_operations(self):
        """Test that security measures don't interfere with legitimate use cases"""
        # Create reports with various valid naming patterns
        valid_reports = [
            "report_123abc.pdf",
            "REPORT_XYZ.PDF",
            "report-with-dashes.pdf",
            "report_v1.0.pdf",
            "monthly_report_2024.pdf",
        ]

        for filename in valid_reports:
            with self.subTest(filename=filename):
                # Create the report file
                report_path = self.reports_dir / filename
                report_path.write_text("Test content")

                # Attempt to download it
                response = self.client.get(
                    f"/report/download/test/{filename}"
                )

                self.assertEqual(
                    response.status_code, 200,
                    f"Valid filename {filename} should be downloadable"
                )


if __name__ == '__main__':
    unittest.main()
