"""
Interfaces for file exporters.

This module defines the abstract base class that all export strategy implementations
must follow, enabling flexible and extensible export mechanisms.
"""

import abc
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


class IFileExporter(abc.ABC):
    """
    Interface for file export strategies.
    
    Implementations of this interface are responsible for exporting the
    extracted documentation content to various file formats.
    """
    
    @abc.abstractmethod
    async def export(
        self, 
        content_map: Dict[str, Dict[str, Any]], 
        output_dir: Union[str, Path],
        project_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export the content to files.
        
        Args:
            content_map: Dictionary mapping URLs to content and metadata
            output_dir: Directory to write the exported files to
            project_name: Name of the project for file naming
            metadata: Additional metadata to include in the export
            
        Returns:
            Dictionary containing export results:
                - 'files': List of exported files with paths and sizes
                - 'total_size': Total size of exported files in bytes
                - 'file_count': Number of files exported
                - 'format': Export format (e.g., 'json', 'markdown')
                
        Raises:
            FileExportError: If the export operation fails
        """
        pass
    
    @property
    @abc.abstractmethod
    def format(self) -> str:
        """
        Get the format of the exporter.
        
        Returns:
            String identifier for the export format
        """
        pass
