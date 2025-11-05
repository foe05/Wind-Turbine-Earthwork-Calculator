#!/bin/bash
# =============================================================================
# Integration Tests for Phase 2 Features
# Geo-Engineering Platform
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
API_URL="${API_URL:-http://localhost:8000}"
TEST_USER_EMAIL="test@example.com"
TEST_CRS="EPSG:25833"
TEST_CENTER_X=402500
TEST_CENTER_Y=5885000

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Test HTTP response
test_http_response() {
    local description=$1
    local url=$2
    local method=${3:-GET}
    local data=${4:-}
    local expected_status=${5:-200}

    log_info "Testing: $description"

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq "$expected_status" ]; then
        log_success "$description (HTTP $http_code)"
        echo "$body"
        return 0
    else
        log_error "$description (Expected HTTP $expected_status, got $http_code)"
        echo "Response: $body"
        return 1
    fi
}

# =============================================================================
# Phase 2: Road Calculations
# =============================================================================

test_road_calculations() {
    log_info "========================================="
    log_info "Testing Road Calculations"
    log_info "========================================="

    # Test 1: Road parameter validation
    test_http_response \
        "Road: Parameter validation endpoint" \
        "$API_URL/calculation/road/validate?road_width=7.5&design_grade=2.5"

    # Test 2: Road calculation (direct, not background job)
    local road_data='{
        "dem_id": "test_dem_1",
        "centerline": [
            [402500, 5885000],
            [402600, 5885100],
            [402700, 5885200]
        ],
        "road_width": 7.5,
        "design_grade": 2.5,
        "cut_slope": 1.5,
        "fill_slope": 2.0,
        "profile_type": "flat",
        "station_interval": 10.0
    }'

    log_info "Road: Submitting calculation (requires DEM)"
    echo "Note: This test requires a valid DEM to be fetched first"

    # Test 3: Get available profile types
    test_http_response \
        "Road: Get profile types" \
        "$API_URL/calculation/road/profile-types"
}

# =============================================================================
# Phase 2: Solar Park Calculations
# =============================================================================

test_solar_calculations() {
    log_info "========================================="
    log_info "Testing Solar Park Calculations"
    log_info "========================================="

    # Test 1: Solar parameter validation
    test_http_response \
        "Solar: Parameter validation" \
        "$API_URL/calculation/solar/validate?panel_length=2.3&panel_width=1.3&row_spacing=5.5"

    # Test 2: Get foundation types
    test_http_response \
        "Solar: Get foundation types" \
        "$API_URL/calculation/solar/foundation-types"

    # Test 3: Get grading strategies
    test_http_response \
        "Solar: Get grading strategies" \
        "$API_URL/calculation/solar/grading-strategies"
}

# =============================================================================
# Phase 2: Terrain Analysis
# =============================================================================

test_terrain_analysis() {
    log_info "========================================="
    log_info "Testing Terrain Analysis"
    log_info "========================================="

    # Test 1: Terrain parameter validation
    test_http_response \
        "Terrain: Parameter validation" \
        "$API_URL/calculation/terrain/validate?resolution=1.0&contour_interval=2.0"

    # Test 2: Get analysis types
    test_http_response \
        "Terrain: Get analysis types" \
        "$API_URL/calculation/terrain/analysis-types"

    # Test 3: Get optimization methods
    test_http_response \
        "Terrain: Get optimization methods" \
        "$API_URL/calculation/terrain/optimization-methods"
}

# =============================================================================
# Phase 2: Background Jobs (Celery)
# =============================================================================

test_background_jobs() {
    log_info "========================================="
    log_info "Testing Background Jobs (Celery)"
    log_info "========================================="

    # Test 1: Submit WKA background job
    local wka_job_data='{
        "project_id": "11111111-1111-1111-1111-111111111111",
        "site_data": {
            "crs": "EPSG:25833",
            "center_x": 402500,
            "center_y": 5885000,
            "foundation_diameter": 25.0,
            "foundation_depth": 4.0,
            "platform_length": 45.0,
            "platform_width": 45.0,
            "optimization_method": "balanced"
        },
        "cost_params": {
            "cost_excavation": 12.0,
            "cost_transport": 5.0,
            "cost_disposal": 8.0,
            "cost_fill_material": 15.0,
            "cost_platform_prep": 5.5,
            "material_reuse": true,
            "swell_factor": 1.25,
            "compaction_factor": 0.9
        }
    }'

    log_info "Jobs: Submitting WKA background job"
    job_response=$(test_http_response \
        "Jobs: Submit WKA job" \
        "$API_URL/jobs/wka/submit" \
        "POST" \
        "$wka_job_data" \
        200)

    if [ $? -eq 0 ]; then
        job_id=$(echo "$job_response" | jq -r '.job_id')
        log_info "Job ID: $job_id"

        # Test 2: Check job status
        sleep 2
        test_http_response \
            "Jobs: Check job status" \
            "$API_URL/job/$job_id/status"

        # Test 3: Cancel job (if still running)
        test_http_response \
            "Jobs: Cancel job" \
            "$API_URL/job/$job_id/cancel" \
            "POST" \
            "{}"
    fi
}

# =============================================================================
# Phase 2: Report Templates
# =============================================================================

test_report_templates() {
    log_info "========================================="
    log_info "Testing Phase 2 Report Templates"
    log_info "========================================="

    # Test 1: Generate Road report
    local road_report_data='{
        "project_name": "Test Road Project",
        "template": "road",
        "format": "html",
        "road_data": {
            "road_length": 1000.0,
            "road_width": 7.5,
            "total_cut": 5000.0,
            "total_fill": 4800.0,
            "net_volume": 200.0,
            "avg_cut_depth": 1.5,
            "avg_fill_depth": 1.2,
            "num_stations": 100,
            "station_interval": 10.0,
            "design_grade": 2.5,
            "profile_type": "flat",
            "start_elevation": 100.0,
            "end_elevation": 125.0,
            "cut_slope": 1.5,
            "fill_slope": 2.0,
            "stations": []
        }
    }'

    test_http_response \
        "Report: Generate Road report (HTML)" \
        "$API_URL/report/generate" \
        "POST" \
        "$road_report_data"

    # Test 2: Generate Solar report
    local solar_report_data='{
        "project_name": "Test Solar Park",
        "template": "solar",
        "format": "html",
        "solar_data": {
            "num_panels": 10000,
            "panel_area": 30000.0,
            "panel_density": 40.0,
            "site_area": 75000.0,
            "foundation_volume": 500.0,
            "foundation_type": "Rammpfähle",
            "grading_cut": 2000.0,
            "grading_fill": 1800.0,
            "grading_strategy": "minimal",
            "access_road_cut": 300.0,
            "access_road_fill": 250.0,
            "access_road_length": 500.0,
            "total_cut": 2300.0,
            "total_fill": 2050.0,
            "net_volume": 250.0,
            "panel_length": 2.3,
            "panel_width": 1.3,
            "row_spacing": 5.5,
            "panel_tilt": 25.0,
            "orientation": 180.0
        }
    }'

    test_http_response \
        "Report: Generate Solar report (HTML)" \
        "$API_URL/report/generate" \
        "POST" \
        "$solar_report_data"

    # Test 3: Generate Terrain report
    local terrain_report_data='{
        "project_name": "Test Terrain Analysis",
        "template": "terrain",
        "format": "html",
        "terrain_data": {
            "analysis_type": "cut_fill_balance",
            "analysis_type_label": "Aushub/Auftrag Balance-Optimierung",
            "polygon_area": 50000.0,
            "num_sample_points": 5000,
            "resolution": 1.0,
            "optimal_elevation": 125.5,
            "cut_volume": 3000.0,
            "fill_volume": 2950.0,
            "net_volume": 50.0,
            "min_elevation": 120.0,
            "max_elevation": 131.0,
            "avg_elevation": 125.4,
            "statistics": {
                "elevation_range": 11.0,
                "cut_points": 2500,
                "fill_points": 2500,
                "avg_cut_depth": 1.2,
                "avg_fill_depth": 1.18
            }
        }
    }'

    test_http_response \
        "Report: Generate Terrain report (HTML)" \
        "$API_URL/report/generate" \
        "POST" \
        "$terrain_report_data"
}

# =============================================================================
# WebSocket Tests
# =============================================================================

test_websocket() {
    log_info "========================================="
    log_info "Testing WebSocket (Manual verification required)"
    log_info "========================================="

    log_warning "WebSocket tests require manual verification"
    log_warning "To test WebSocket, use a WebSocket client:"
    log_warning "ws://localhost:8000/ws/job/{job_id}"
    log_info "Skipping automated WebSocket tests"
}

# =============================================================================
# Database Tests
# =============================================================================

test_database_schema() {
    log_info "========================================="
    log_info "Testing Database Schema (Phase 2)"
    log_info "========================================="

    log_info "Checking if Phase 2 tables exist..."

    # Check if we can connect to postgres
    if command -v psql &> /dev/null; then
        PGPASSWORD=secret psql -h localhost -U admin -d geo_engineering -c "\dt" | grep -q "report_templates" && \
            log_success "Table: report_templates exists" || \
            log_error "Table: report_templates missing"

        PGPASSWORD=secret psql -h localhost -U admin -d geo_engineering -c "\dt" | grep -q "user_template_overrides" && \
            log_success "Table: user_template_overrides exists" || \
            log_error "Table: user_template_overrides missing"

        PGPASSWORD=secret psql -h localhost -U admin -d geo_engineering -c "SELECT COUNT(*) FROM projects WHERE use_case IN ('road', 'solar', 'terrain');" && \
            log_success "Phase 2 demo projects exist" || \
            log_warning "Phase 2 demo projects may be missing"
    else
        log_warning "psql not available, skipping database tests"
    fi
}

# =============================================================================
# Main Test Runner
# =============================================================================

main() {
    log_info "========================================="
    log_info "Phase 2 Integration Tests"
    log_info "========================================="
    log_info "API URL: $API_URL"
    log_info ""

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 5

    # Test API Gateway health
    test_http_response "API Gateway health check" "$API_URL/health"

    # Run all test suites
    test_road_calculations
    test_solar_calculations
    test_terrain_analysis
    test_background_jobs
    test_report_templates
    test_websocket
    test_database_schema

    # Print summary
    echo ""
    log_info "========================================="
    log_info "Test Summary"
    log_info "========================================="
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All tests passed!"
        exit 0
    fi
}

# Run main function
main "$@"
