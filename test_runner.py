#!/usr/bin/env python3
"""
Simple test runner for validation tests
"""
import sys
import os

# Add plugin directory to path
plugin_dir = os.path.join(os.path.dirname(__file__), 'windturbine_earthwork_calculator_v2')
sys.path.insert(0, plugin_dir)

# Run tests
import unittest

# Load test module
from tests import test_validation_enhanced

# Create test suite
loader = unittest.TestLoader()
suite = loader.loadTestsFromModule(test_validation_enhanced)

# Run tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Exit with proper code
sys.exit(0 if result.wasSuccessful() else 1)
