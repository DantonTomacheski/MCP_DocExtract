#!/usr/bin/env python3
"""
Test runner for DocExtract AI.

This script runs the unit tests for the project, with a focus on the MCP server components.
"""

import os
import sys
import pytest


def main():
    """Run the unit tests."""
    # Add the project root to the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    
    # Default arguments
    args = [
        "-v",  # Verbose output
        "--cov=src/server",  # Coverage for server module
        "--cov-report=term",  # Terminal coverage report
        "tests/unit/server"  # Test directory
    ]
    
    # Add any command-line arguments
    args.extend(sys.argv[1:])
    
    # Run the tests
    return pytest.main(args)


if __name__ == "__main__":
    sys.exit(main())
