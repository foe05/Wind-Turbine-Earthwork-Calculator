#!/bin/bash
# Security Testing Script for Path Traversal Vulnerability Fix
# This script performs end-to-end security verification of the report download endpoint

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPORT_SERVICE_URL="${REPORT_SERVICE_URL:-http://localhost:8005}"
TEST_REPORT_ID="test-report-123"
TEST_VALID_FILENAME="test-report.pdf"

echo "=================================================="
echo "Security Testing: Path Traversal Vulnerability Fix"
echo "=================================================="
echo ""
echo "Testing endpoint: ${REPORT_SERVICE_URL}"
echo ""

# Function to test an endpoint
test_endpoint() {
    local test_name="$1"
    local url="$2"
    local expected_status="$3"
    local description="$4"

    echo "----------------------------------------"
    echo "Test: ${test_name}"
    echo "Description: ${description}"
    echo "URL: ${url}"
    echo "Expected Status: ${expected_status}"
    echo ""

    # Make request and capture status code
    response=$(curl -s -w "\n%{http_code}" -X GET "${url}" 2>&1)
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    echo "Received Status: ${status_code}"

    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "Response body: ${body}"
    fi
    echo ""
}

# Test 1: Valid filename (legitimate use case)
echo "=== LEGITIMATE USE CASE TESTS ==="
echo ""

test_endpoint \
    "Valid PDF Download" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/${TEST_VALID_FILENAME}" \
    "200" \
    "Should successfully download a valid report file"

test_endpoint \
    "Valid HTML Download" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/report.html" \
    "200" \
    "Should successfully download a valid HTML report"

# Test 2: Path traversal attempts (SECURITY TESTS)
echo "=== SECURITY TESTS - PATH TRAVERSAL ATTACKS ==="
echo ""

test_endpoint \
    "Path Traversal - Parent Directory (.env)" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/../../.env" \
    "400" \
    "Should reject attempt to access .env file using ../"

test_endpoint \
    "Path Traversal - System Files (etc/passwd)" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/../../../etc/passwd" \
    "400" \
    "Should reject attempt to access /etc/passwd using ../"

test_endpoint \
    "Path Traversal - Multiple Levels" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/../../../../../../../../etc/shadow" \
    "400" \
    "Should reject deeply nested path traversal attempt"

test_endpoint \
    "Absolute Path - /etc/passwd" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}//etc/passwd" \
    "400" \
    "Should reject absolute path access attempt"

test_endpoint \
    "Absolute Path - /root/.ssh/id_rsa" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}//root/.ssh/id_rsa" \
    "400" \
    "Should reject attempt to access SSH private keys"

# Windows-style path traversal
test_endpoint \
    "Windows Path Traversal - Backslashes" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/..\\..\\windows\\system32\\config\\sam" \
    "400" \
    "Should reject Windows-style path traversal with backslashes"

test_endpoint \
    "Windows Path Traversal - Mixed Slashes" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/..\\.\\../.env" \
    "400" \
    "Should reject mixed slash path traversal"

# URL-encoded path traversal
test_endpoint \
    "URL-Encoded Traversal - %2e%2e%2f" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/%2e%2e%2f%2e%2e%2f.env" \
    "400" \
    "Should reject URL-encoded path traversal (%2e%2e%2f = ../)"

test_endpoint \
    "URL-Encoded Traversal - %2e%2e/" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/%2e%2e/%2e%2e/etc/passwd" \
    "400" \
    "Should reject partially URL-encoded path traversal"

# Null byte injection
test_endpoint \
    "Null Byte Injection" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/../../.env%00.pdf" \
    "400" \
    "Should reject null byte injection attempt"

# Empty and edge cases
test_endpoint \
    "Empty Filename" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/" \
    "400" \
    "Should reject empty filename"

test_endpoint \
    "Dot Filename" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/." \
    "400" \
    "Should reject single dot filename"

test_endpoint \
    "Double Dot Filename" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/.." \
    "400" \
    "Should reject double dot filename"

# Test 3: Non-existent file (should return 404, not 400)
echo "=== ERROR HANDLING TESTS ==="
echo ""

test_endpoint \
    "Non-Existent File" \
    "${REPORT_SERVICE_URL}/report/download/${TEST_REPORT_ID}/nonexistent-file.pdf" \
    "404" \
    "Should return 404 for non-existent but valid filename"

echo "=================================================="
echo "Checking Docker Logs for Security Events"
echo "=================================================="
echo ""

# Check logs for security warnings
echo "Looking for security-related log entries..."
echo ""

if command -v docker &> /dev/null; then
    echo "=== Recent security-related log entries ==="
    docker logs geo_report --tail 100 2>&1 | grep -i -E "(security|traversal|invalid|path|rejected|warning|error)" || echo "No security-related logs found (this might be OK if no attacks were attempted)"
    echo ""

    echo "=== All recent logs (last 50 lines) ==="
    docker logs geo_report --tail 50 2>&1
else
    echo -e "${YELLOW}Docker command not available. Please manually check logs:${NC}"
    echo "docker logs geo_report | grep -i 'security\\|traversal\\|invalid path'"
fi

echo ""
echo "=================================================="
echo "Security Testing Complete"
echo "=================================================="
echo ""
echo "VERIFICATION CHECKLIST:"
echo "□ All legitimate file downloads returned 200"
echo "□ All path traversal attempts returned 400"
echo "□ All absolute path attempts returned 400"
echo "□ All URL-encoded attacks returned 400"
echo "□ Non-existent files returned 404 (not 400)"
echo "□ Security events are logged"
echo "□ Error messages don't leak path information"
echo ""
echo "Review the test results above and verify all tests passed."
