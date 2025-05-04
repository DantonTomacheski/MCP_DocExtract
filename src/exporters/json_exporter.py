"""
JSON exporter implementation.

This module implements a strategy for exporting the extracted content to JSON format,
organizing the content with proper structure and metadata.
"""

import os
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

from src.exporters.interfaces import IFileExporter
from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class JSONExporter(IFileExporter):
    """
    JSON exporter implementation.
    
    This class implements the IFileExporter interface for JSON format exports,
    producing structured JSON files with proper formatting and organization.
    """
    
    def __init__(self, pretty_print: bool = True):
        """Initialize the JSON exporter.
        
        Args:
            pretty_print: Whether to format the JSON with indentation (default: True)
        """
        self._pretty_print = pretty_print
    
    @property
    def format(self) -> str:
        """
        Get the format of the exporter.
        
        Returns:
            String identifier for the export format
        """
        return "json"
    
    async def export(
        self, 
        content_map: Dict[str, Dict[str, Any]], 
        output_dir: Union[str, Path],
        project_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export the content to JSON files.
        
        Args:
            content_map: Dictionary mapping URLs to content and metadata
            output_dir: Directory to write the exported files to
            project_name: Name of the project for file naming
            metadata: Additional metadata to include in the export
            
        Returns:
            Dictionary containing export results
            
        Raises:
            FileExportError: If the export operation fails
        """
        # Convert string path to Path object
        output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize export results
        export_results = {
            "files": [],
            "total_size": 0,
            "file_count": 0,
            "format": self.format
        }
        
        try:
            # Prepare export data
            output_data = self._prepare_export_data(content_map, project_name, metadata)
            
            # Sanitize project name for filename
            safe_project_name = self._sanitize_filename(project_name)
            
            # Create full export file
            full_export_path = output_dir / f"{safe_project_name}.json"
            
            # Write JSON content with indentation based on pretty_print setting
            with open(full_export_path, "w", encoding="utf-8") as f:
                indent = 2 if self._pretty_print else None
                json.dump(output_data, f, ensure_ascii=False, indent=indent)
            
            # Get file size
            file_size = os.path.getsize(full_export_path)
            
            # Record export results
            export_results["files"].append({
                "path": str(full_export_path),
                "size": file_size,
                "url_count": len(content_map)
            })
            export_results["total_size"] += file_size
            export_results["file_count"] += 1
            
            # Create individual page JSON files if there are many pages
            if len(content_map) > 10:
                # Create pages directory
                pages_dir = output_dir / f"{safe_project_name}_pages"
                os.makedirs(pages_dir, exist_ok=True)
                
                # Write individual page files
                for i, (url, content_data) in enumerate(content_map.items()):
                    # Create safe filename
                    page_number = str(i + 1).zfill(3)
                    page_title = content_data.get("title", f"page_{page_number}")
                    safe_title = self._sanitize_filename(page_title)
                    page_file = pages_dir / f"{page_number}_{safe_title}.json"
                    
                    # Prepare page data
                    page_data = {
                        "url": url,
                        "title": content_data.get("title", ""),
                        "content": content_data.get("content", ""),
                        "metadata": content_data.get("metadata", {}),
                        "elements": content_data.get("elements", {})
                    }
                    
                    # Write the page file
                    with open(page_file, 'w', encoding='utf-8') as f:
                        json.dump(page_data, f, indent=2, ensure_ascii=False)
                    
                    # Get file size
                    file_size = os.path.getsize(page_file)
                    
                    # Record export results
                    export_results["files"].append({
                        "path": str(page_file),
                        "size": file_size,
                        "url": url
                    })
                    export_results["total_size"] += file_size
                    export_results["file_count"] += 1
            
            logger.info(f"Exported {len(content_map)} pages to JSON format")
            logger.info(f"Total export size: {export_results['total_size']} bytes")
            
            return export_results
            
        except Exception as e:
            error_msg = f"Error exporting to JSON: {str(e)}"
            logger.error(error_msg)
            raise FileExportError(error_msg) from e
    
    def _prepare_export_data(
        self, 
        content_map: Dict[str, Dict[str, Any]], 
        project_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare the export data structure.
        
        Args:
            content_map: Dictionary mapping URLs to content and metadata
            project_name: Name of the project
            metadata: Additional metadata to include
            
        Returns:
            Dictionary with structured export data
        """
        # Basic export structure
        output_data = {
            "metadata": metadata or {},
            "content": [
                {
                    "url": url,
                    "title": data.get("title", ""),
                    "content": data.get("content", ""),
                    "metadata": data.get("metadata", {})
                } for url, data in content_map.items()
            ]
        }
        
        return output_data
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a string to make it safe for use as a filename.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Trim whitespace and limit length
        filename = filename.strip()[:100]
        
        # Ensure we have at least some characters
        if not filename:
            filename = "untitled"
            
        return filename


class FileExportError(Exception):
    """Exception raised when file export operations fail."""
    pass
