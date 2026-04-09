#!/usr/bin/env python3
"""Verify all new modules can be imported"""
import sys
import os

# Add plugin directory to path
plugin_dir = os.path.join(os.path.dirname(__file__), 'windturbine_earthwork_calculator_v2')
sys.path.insert(0, plugin_dir)

print("Testing module imports...")
print("=" * 50)

try:
    print("1. Testing i18n module...")
    from utils.i18n import get_message, set_language, get_language, detect_qgis_locale
    print("   ✓ i18n module imported successfully")
    print(f"   - Functions: get_message, set_language, get_language, detect_qgis_locale")

    print("\n2. Testing error_messages module...")
    from utils.error_messages import ERROR_MESSAGES, get_error_keys, validate_error_messages
    print(f"   ✓ error_messages module imported successfully")
    print(f"   - {len(ERROR_MESSAGES)} error messages loaded")
    print(f"   - Functions: get_error_keys, validate_error_messages")

    print("\n3. Testing updated validation module...")
    from utils.validation import (
        validate_file_exists,
        validate_height_range,
        validate_crs,
        validate_polygon,
        validate_polygon_topology,
        validate_raster_layer,
        ValidationError
    )
    print("   ✓ validation module imported successfully")
    print("   - Functions: validate_file_exists, validate_height_range, validate_crs,")
    print("     validate_polygon, validate_polygon_topology, validate_raster_layer")

    print("\n4. Testing language switching...")
    set_language('de')
    msg_de = get_message('file_not_found', ERROR_MESSAGES, file_path='/test/path.txt')
    print(f"   ✓ German message: {msg_de[:50]}...")

    set_language('en')
    msg_en = get_message('file_not_found', ERROR_MESSAGES, file_path='/test/path.txt')
    print(f"   ✓ English message: {msg_en[:50]}...")

    print("\n5. Verifying error message structure...")
    validate_error_messages()
    print(f"   ✓ All {len(ERROR_MESSAGES)} error messages validated")

    print("\n" + "=" * 50)
    print("✅ ALL IMPORTS SUCCESSFUL!")
    print("=" * 50)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
