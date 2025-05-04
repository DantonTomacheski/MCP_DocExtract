"""
API documentation configuration for DocExtract AI.

This module provides enhanced OpenAPI documentation configuration
with examples, descriptions, and other metadata to make the API
more user-friendly and self-documenting.
"""

from typing import Dict, Any

# API metadata for OpenAPI docs
api_metadata = {
    "title": "DocExtract AI API",
    "description": """
    # DocExtract AI Documentation Extraction API
    
    This API provides tools for extracting, processing, and exporting documentation content from websites.
    It includes AI-powered content cleaning and structural enhancement capabilities.
    
    ## Key Features
    
    * Website documentation extraction with customizable depth and concurrency
    * AI-powered content cleaning and enhancement
    * Multiple export formats (JSON, Markdown)
    * Framework detection for optimal extraction strategy selection
    * Asynchronous processing with status tracking
    
    ## Authentication
    
    API requests require authentication using an API key provided in the `X-API-Key` header.
    Contact the administrator to obtain an API key.
    
    ## Rate Limits
    
    * 60 requests per minute for extraction operations
    * 120 requests per minute for status checks
    * 30 requests per minute for content processing operations
    
    ## Support
    
    For issues or feature requests, please contact support@example.com
    """,
    "version": "1.0.0",
    "contact": {
        "name": "API Support",
        "email": "support@example.com",
        "url": "https://github.com/dtomacheski/DocExtract AI/issues"
    },
    "license_info": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
}

# Examples for API endpoints
api_examples: Dict[str, Dict[str, Any]] = {
    "extract_document": {
        "request": {
            "url": "https://docs.python.org/3/",
            "mode": "auto",
            "parallel": True,
            "max_depth": 3,
            "concurrency": 5,
            "use_ai": True,
            "filters": {
                "include_patterns": ["*/library/*", "*/reference/*"],
                "exclude_patterns": ["*/whatsnew/*", "*/download/*"]
            }
        },
        "response": {
            "operation_id": "ex_429f8c59abcd",
            "status": "running",
            "message": "Extraction started successfully"
        }
    },
    "process_content": {
        "request": {
            "content": "<div class=\"documentation\"><h1>API Reference</h1><p>This is some documentation content.</p>...</div>",
            "content_type": "html",
            "processing_mode": "clean_and_structure",
            "context": {
                "url": "https://docs.example.com/api",
                "title": "API Reference"
            }
        },
        "response": {
            "content": "# API Reference\n\nThis is some documentation content...",
            "format": "markdown",
            "metadata": {
                "processing_time_ms": 234,
                "ai_enhanced": True
            }
        }
    },
    "export_content": {
        "request": {
            "operation_id": "ex_429f8c59abcd",
            "format": "markdown",
            "project_name": "Python Documentation",
            "include_metadata": True
        },
        "response": {
            "operation_id": "exp_527d9e68efgh",
            "status": "completed",
            "exports": [
                {
                    "file_path": "/exports/python_docs.md",
                    "file_size": 1245678,
                    "page_count": 320,
                    "format": "markdown"
                }
            ]
        }
    },
    "check_status": {
        "request": {
            "operation_id": "ex_429f8c59abcd",
            "include_details": True
        },
        "response": {
            "operation_id": "ex_429f8c59abcd",
            "operation_type": "extraction",
            "status": "running",
            "progress": 45.5,
            "message": "Processing page 45 of 99",
            "details": {
                "pages_processed": 45,
                "pages_total": 99,
                "current_url": "https://docs.python.org/3/library/asyncio.html",
                "elapsed_time_seconds": 67,
                "estimated_completion_time": "2023-04-15T15:30:45Z",
                "queue_size": 54
            }
        }
    },
    "detect_framework": {
        "request": {
            "url": "https://reactjs.org/docs/getting-started.html"
        },
        "response": {
            "framework": "docusaurus",
            "confidence": 0.92,
            "indicators": [
                "Docusaurus meta tags detected",
                "React-style navigation structure",
                "Algolia DocSearch integration"
            ]
        }
    }
}


def get_openapi_config() -> Dict[str, Any]:
    """
    Get the complete OpenAPI configuration for the API.
    
    Returns:
        OpenAPI configuration dictionary
    """
    return {
        "metadata": api_metadata,
        "examples": api_examples
    }
