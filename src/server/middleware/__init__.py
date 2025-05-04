"""
Middleware modules for the DocExtract AI server.

This package contains middleware components that provide
cross-cutting functionality like authentication, logging,
and error handling for the server.
"""

from typing import List

# Import middlewares for easy access
try:
    from .auth import add_auth_middleware, ApiKeyAuth
except ImportError:
    # Auth middleware may not be available yet
    pass
