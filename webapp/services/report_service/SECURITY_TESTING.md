# Security Testing Guide: Path Traversal Vulnerability Fix

## Overview

This document provides comprehensive instructions for manually testing the path traversal vulnerability fix in the report download endpoint.

## Vulnerability Background

**Fixed Issue:** The `/report/download/{report_id}/{filename}` endpoint previously accepted user-controlled filenames without validation, allowing path traversal attacks to access arbitrary files on the server.

**Fix Applied:** Added `validate_safe_path()` function that:
- Rejects path traversal sequences (`../`, `..`, `\`, etc.)
- Validates paths using canonicalization (`Path.resolve()`)
- Ensures resolved paths stay within the reports directory
- Logs security events
- Returns appropriate HTTP status codes (400 for invalid paths, 404 for missing files)

## Prerequisites

1. Docker and docker-compose installed
2. Services configured and ready to run
3. `curl` or similar HTTP client installed

## Test Setup

### Step 1: Start Services

```bash
cd webapp
docker-compose up -d postgres redis report_service
```

Wait for services to be healthy:

```bash
# Check service status
docker-compose ps

# Check report_service logs
docker logs geo_report
```

### Step 2: Verify Service is Running

```bash
# Check health endpoint
curl http://localhost:8005/health

# Expected: 200 OK
```

### Step 3: Generate a Test Report (Optional)

If you need to test with a real report file:

```bash
# This depends on your API Gateway being up and having auth
# Adjust according to your actual API structure
curl -X POST http://localhost:8000/api/report/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"turbine_count": 5, "foundation_type": "gravity"}'
```

## Security Test Cases

### Test Suite 1: Legitimate Use Cases ✅

These should **PASS** (return 200):

```bash
# Test 1: Valid PDF download
curl -v http://localhost:8005/report/download/test-123/report.pdf

# Test 2: Valid HTML download
curl -v http://localhost:8005/report/download/test-123/report.html

# Test 3: Valid filename with UUID
curl -v http://localhost:8005/report/download/550e8400-e29b-41d4-a716-446655440000/earthwork-report.pdf
```

**Expected Result:** 200 OK (or 404 if file doesn't exist, which is acceptable)

---

### Test Suite 2: Path Traversal Attacks 🚨

These should **FAIL** (return 400):

#### 2.1: Basic Path Traversal

```bash
# Test: Access .env file
curl -v http://localhost:8005/report/download/test-123/../../.env

# Test: Access /etc/passwd
curl -v http://localhost:8005/report/download/test-123/../../../etc/passwd

# Test: Deep nested traversal
curl -v http://localhost:8005/report/download/test-123/../../../../../../../../etc/shadow
```

**Expected Result:** 400 Bad Request with error message "Invalid filename"

#### 2.2: Absolute Path Attempts

```bash
# Test: Absolute path to /etc/passwd
curl -v http://localhost:8005/report/download/test-123//etc/passwd

# Test: Absolute path to SSH keys
curl -v http://localhost:8005/report/download/test-123//root/.ssh/id_rsa

# Test: Absolute path to application files
curl -v http://localhost:8005/report/download/test-123//app/.env
```

**Expected Result:** 400 Bad Request

#### 2.3: Windows-Style Path Traversal

```bash
# Test: Windows backslashes
curl -v http://localhost:8005/report/download/test-123/..\\..\\windows\\system32\\config\\sam

# Test: Mixed slashes
curl -v "http://localhost:8005/report/download/test-123/..\\.\\../.env"

# Test: Windows absolute path
curl -v "http://localhost:8005/report/download/test-123/C:\\Windows\\System32\\config\\sam"
```

**Expected Result:** 400 Bad Request

#### 2.4: URL-Encoded Attacks

```bash
# Test: URL-encoded ../ (%2e%2e%2f)
curl -v http://localhost:8005/report/download/test-123/%2e%2e%2f%2e%2e%2f.env

# Test: Partially encoded
curl -v http://localhost:8005/report/download/test-123/%2e%2e/etc/passwd

# Test: Double-encoded
curl -v http://localhost:8005/report/download/test-123/%252e%252e%252f.env
```

**Expected Result:** 400 Bad Request

#### 2.5: Null Byte Injection

```bash
# Test: Null byte to bypass extension check
curl -v http://localhost:8005/report/download/test-123/../../.env%00.pdf

# Test: Null byte in middle
curl -v "http://localhost:8005/report/download/test-123/report%00../../.env"
```

**Expected Result:** 400 Bad Request

#### 2.6: Edge Cases

```bash
# Test: Empty filename
curl -v http://localhost:8005/report/download/test-123/

# Test: Single dot
curl -v http://localhost:8005/report/download/test-123/.

# Test: Double dot
curl -v http://localhost:8005/report/download/test-123/..

# Test: Just slashes
curl -v http://localhost:8005/report/download/test-123///
```

**Expected Result:** 400 Bad Request

---

### Test Suite 3: Error Handling ℹ️

#### 3.1: Non-Existent Files

```bash
# Test: Valid filename but file doesn't exist
curl -v http://localhost:8005/report/download/test-123/nonexistent.pdf

# Test: Valid UUID but file doesn't exist
curl -v http://localhost:8005/report/download/550e8400-e29b-41d4-a716-446655440000/report.pdf
```

**Expected Result:** 404 Not Found (NOT 400 - this is important!)

---

## Automated Testing Script

Run the comprehensive test script:

```bash
cd webapp/services/report_service
./security-test.sh
```

The script will:
1. Test all legitimate use cases
2. Attempt all path traversal attacks
3. Verify proper error handling
4. Check Docker logs for security events

## Log Verification

### Check Security Event Logging

```bash
# View recent logs
docker logs geo_report --tail 100

# Filter for security events
docker logs geo_report | grep -i 'security\|traversal\|invalid'

# Filter for warnings
docker logs geo_report | grep -i 'warning\|error'

# Follow logs in real-time while testing
docker logs -f geo_report
```

**Expected Log Entries:**

For attack attempts:
```
WARNING: Path traversal attempt detected: ../../.env
WARNING: Invalid path rejected: /etc/passwd
```

For successful downloads:
```
INFO: Report downloaded: test-123/report.pdf
```

### Verify Error Messages Don't Leak Information

Check that error responses:
- ✅ Return generic "Invalid filename" message
- ❌ Do NOT reveal actual file paths
- ❌ Do NOT reveal directory structure
- ❌ Do NOT expose system information

Example of **GOOD** error response:
```json
{"detail": "Invalid filename"}
```

Example of **BAD** error response (this should NOT happen):
```json
{"detail": "Path /etc/passwd is outside /app/reports"}
```

## Verification Checklist

After running all tests, verify:

- [ ] All legitimate file downloads return 200 OK (or 404 if file missing)
- [ ] All path traversal attempts with `../` return 400 Bad Request
- [ ] All absolute path attempts return 400 Bad Request
- [ ] All Windows-style path attacks return 400 Bad Request
- [ ] All URL-encoded attacks return 400 Bad Request
- [ ] All null byte injection attempts return 400 Bad Request
- [ ] Non-existent valid files return 404 Not Found (not 400)
- [ ] Security events are logged properly
- [ ] Error messages are generic and don't leak path information
- [ ] Service remains stable under attack attempts
- [ ] No regression in legitimate functionality

## Common Issues and Troubleshooting

### Issue: Service Not Starting

```bash
# Check logs
docker logs geo_report

# Check if port is already in use
lsof -i :8005

# Rebuild if needed
docker-compose build report_service
docker-compose up -d report_service
```

### Issue: Tests Returning 500 Instead of 400

This indicates an unhandled exception. Check:
1. Logs for Python tracebacks
2. That `validate_safe_path()` is properly imported
3. That exception handling is in place

### Issue: Tests Returning 200 for Attacks

This is **CRITICAL**. It means the fix is not working:
1. Verify the code changes are applied
2. Check that the container is using the updated code
3. Rebuild the container: `docker-compose build report_service`
4. Restart: `docker-compose restart report_service`

## Security Best Practices Verified

This fix implements:

1. **Input Validation:** All filenames are validated before use
2. **Path Canonicalization:** Paths are resolved to their canonical form
3. **Boundary Checking:** Resolved paths must be within the allowed directory
4. **Deny-List + Allow-List:** Both dangerous patterns blocked AND path must be in valid directory
5. **Security Logging:** Attack attempts are logged for monitoring
6. **Safe Error Messages:** Errors don't reveal system structure
7. **Defense in Depth:** Multiple layers of validation

## Additional Security Considerations

While this fix addresses the path traversal vulnerability, consider:

1. **Authentication:** Ensure the endpoint requires proper authentication
2. **Authorization:** Verify users can only access their own reports
3. **Rate Limiting:** Prevent brute-force filename guessing
4. **Audit Logging:** Log all download attempts for security monitoring
5. **File Permissions:** Ensure reports directory has minimal permissions
6. **Monitoring:** Set up alerts for repeated path traversal attempts

## Acceptance Criteria

For QA sign-off, all of the following must be true:

✅ All unit tests pass (`pytest tests/test_security.py`)
✅ All integration tests pass (`pytest tests/test_report_api.py`)
✅ All manual security tests fail with 400 as expected
✅ Legitimate downloads still work (return 200 or 404)
✅ Security events are logged
✅ Error messages don't leak information
✅ No regression in existing functionality
✅ Service remains stable under attack attempts

## References

- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- CWE-22: Improper Limitation of a Pathname: https://cwe.mitre.org/data/definitions/22.html
- Security Utils Implementation: `webapp/services/report_service/app/utils/security.py`
- Fixed Endpoint: `webapp/services/report_service/app/api/report.py`
