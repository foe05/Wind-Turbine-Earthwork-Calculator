# Security Testing Quick Reference

## Quick Start

```bash
# 1. Start services
cd webapp && docker-compose up -d report_service

# 2. Run automated tests
cd services/report_service && ./security-test.sh

# 3. Check logs
docker logs geo_report | grep -i security
```

## Manual Test Commands

### ✅ Should Return 200 (Valid)
```bash
curl -v http://localhost:8005/report/download/test-123/report.pdf
curl -v http://localhost:8005/report/download/test-123/report.html
```

### 🚨 Should Return 400 (Attacks)
```bash
# Path traversal
curl -v http://localhost:8005/report/download/test-123/../../.env
curl -v http://localhost:8005/report/download/test-123/../../../etc/passwd

# Absolute paths
curl -v http://localhost:8005/report/download/test-123//etc/passwd

# Windows style
curl -v http://localhost:8005/report/download/test-123/..\\..\\windows\\system32

# URL encoded
curl -v http://localhost:8005/report/download/test-123/%2e%2e%2f.env

# Null bytes
curl -v http://localhost:8005/report/download/test-123/../../.env%00.pdf

# Edge cases
curl -v http://localhost:8005/report/download/test-123/..
curl -v http://localhost:8005/report/download/test-123/.
```

### ℹ️ Should Return 404 (Missing)
```bash
curl -v http://localhost:8005/report/download/test-123/nonexistent.pdf
```

## Expected Results

| Test Type | HTTP Status | Response |
|-----------|-------------|----------|
| Valid file | 200 | File content |
| Valid but missing | 404 | "Report not found" |
| Path traversal | 400 | "Invalid filename" |
| Absolute path | 400 | "Invalid filename" |
| Malicious input | 400 | "Invalid filename" |

## Verification Checklist

- [ ] Service starts without errors
- [ ] Valid downloads work (200)
- [ ] All attacks blocked (400)
- [ ] Missing files return 404
- [ ] Logs show security events
- [ ] Error messages are generic
- [ ] No system info leaked

## Log Analysis

```bash
# Real-time monitoring
docker logs -f geo_report

# Security events
docker logs geo_report | grep -i "security\|traversal\|invalid"

# Last 50 lines
docker logs geo_report --tail 50
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8005 in use | `docker-compose restart report_service` |
| Returns 500 | Check logs for exceptions |
| Returns 200 for attacks | Rebuild container |
| Service won't start | Check `docker logs geo_report` |

## One-Liner Full Test

```bash
cd webapp && docker-compose up -d report_service && \
cd services/report_service && ./security-test.sh && \
echo "Check logs:" && docker logs geo_report --tail 20
```
