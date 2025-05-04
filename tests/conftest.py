"""
Pytest configuration for DocExtract AI test suite.
"""

import pytest
import os
import sys

# Add the src directory to PYTHONPATH so imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
