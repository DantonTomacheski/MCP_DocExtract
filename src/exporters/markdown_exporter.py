"""
Markdown exporter implementation.

This module implements a strategy for exporting the extracted content to Markdown format,
preserving the document structure and formatting for readability.
"""

import os
import re
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, Comment
import html2text

from src.exporters.interfaces import IFileExporter
from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class MarkdownExporter(IFileExporter):
    """
    Markdown exporter implementation.
    
    This class implements the IFileExporter interface for Markdown format exports,
    producing well-formatted Markdown files with proper structure and navigation.
    """
    
    def __init__(
        self,
        table_of_contents: bool = True,
        include_links: bool = True,
        include_images: bool = True,
        github_flavored: bool = True
    ):
        """
        Initialize the Markdown exporter.
        
        Args:
            table_of_contents: Whether to include a table of contents (default: True)
            include_links: Whether to preserve links (default: True)
            include_images: Whether to include image references (default: True)
            github_flavored: Whether to use GitHub-flavored Markdown (default: True)
        """
        self._table_of_contents = table_of_contents
        self._include_links = include_links
        self._include_images = include_images
        self._github_flavored = github_flavored
        
        # Configure html2text converter
        self._converter = html2text.HTML2Text()
        self._converter.unicode_snob = True
        self._converter.body_width = 0  # Don't wrap lines
        self._converter.ignore_links = not include_links
        self._converter.ignore_images = not include_images
        self._converter.ignore_tables = False
        self._converter.mark_code = True
        self._converter.escape_snob = False
        self._converter.wrap_links = False
        self._converter.emphasis_mark = '*'  # Use asterisks for italics
        
        # GitHub-flavored Markdown uses triple backticks for code blocks
        if github_flavored:
            self._converter.code_block_open_tag = "```{language}\n"
            self._converter.code_block_close_tag = "```\n\n"
    
    @property
    def format(self) -> str:
        """
        Get the format of the exporter.
        
        Returns:
            String identifier for the export format
        """
        return "markdown"
    
    async def export(
        self, 
        content_map: Dict[str, Dict[str, Any]], 
        output_dir: Union[str, Path],
        project_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export the content to Markdown files.
        
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
            # Sanitize project name for filename
            safe_project_name = self._sanitize_filename(project_name)
            
            # Create full export file
            full_export_path = output_dir / f"{safe_project_name}.md"
            
            # Generate the combined Markdown file
            with open(full_export_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"# {project_name}\n\n")
                
                # Write metadata
                f.write("## Metadata\n\n")
                f.write(f"- **Extracted at**: {datetime.now().isoformat()}\n")
                f.write(f"- **Page count**: {len(content_map)}\n")
                
                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            f.write(f"- **{key}**: {value}\n")
                
                f.write("\n")
                
                # Write table of contents if enabled
                if self._table_of_contents and len(content_map) > 1:
                    f.write("## Table of Contents\n\n")
                    
                    for i, (url, content_data) in enumerate(content_map.items()):
                        title = content_data.get("title", f"Page {i+1}")
                        sanitized_title = self._make_anchor(title)
                        f.write(f"- [{title}](#{sanitized_title})\n")
                    
                    f.write("\n---\n\n")
                
                # Write each page
                for i, (url, content_data) in enumerate(content_map.items()):
                    title = content_data.get("title", f"Page {i+1}")
                    content_html = content_data.get("content", "")
                    depth = content_data.get("metadata", {}).get("depth", 0)
                    
                    # Write page header
                    f.write(f"## {title}\n\n")
                    
                    # Write page metadata
                    f.write(f"*Source: [{url}]({url})*\n\n")
                    if depth is not None:
                        f.write(f"*Depth: {depth}*\n\n")
                    
                    # Convert HTML to Markdown and write content
                    markdown_content = self._html_to_markdown(content_html)
                    f.write(markdown_content)
                    
                    # Add separator between pages
                    if i < len(content_map) - 1:
                        f.write("\n\n---\n\n")
            
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
            
            # Create individual page Markdown files if there are many pages
            if len(content_map) > 10:
                # Create pages directory
                pages_dir = output_dir / f"{safe_project_name}_pages"
                os.makedirs(pages_dir, exist_ok=True)
                
                # Create an index file
                index_path = pages_dir / "README.md"
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {project_name} Documentation\n\n")
                    f.write("## Pages\n\n")
                    
                    for i, (url, content_data) in enumerate(content_map.items()):
                        page_number = str(i + 1).zfill(3)
                        title = content_data.get("title", f"Page {i+1}")
                        safe_title = self._sanitize_filename(title)
                        page_filename = f"{page_number}_{safe_title}.md"
                        
                        f.write(f"- [{title}]({page_filename})\n")
                
                # Get index file size
                index_size = os.path.getsize(index_path)
                export_results["files"].append({
                    "path": str(index_path),
                    "size": index_size
                })
                export_results["total_size"] += index_size
                export_results["file_count"] += 1
                
                # Write individual page files
                for i, (url, content_data) in enumerate(content_map.items()):
                    # Create safe filename
                    page_number = str(i + 1).zfill(3)
                    title = content_data.get("title", f"Page {i+1}")
                    safe_title = self._sanitize_filename(title)
                    page_file = pages_dir / f"{page_number}_{safe_title}.md"
                    
                    # Write the page file
                    with open(page_file, 'w', encoding='utf-8') as f:
                        # Write page header
                        f.write(f"# {title}\n\n")
                        
                        # Write page metadata
                        f.write(f"*Source: [{url}]({url})*\n\n")
                        depth = content_data.get("metadata", {}).get("depth", 0)
                        if depth is not None:
                            f.write(f"*Depth: {depth}*\n\n")
                        
                        # Add back link to index
                        f.write(f"[Back to Index](README.md)\n\n---\n\n")
                        
                        # Convert HTML to Markdown and write content
                        content_html = content_data.get("content", "")
                        markdown_content = self._html_to_markdown(content_html)
                        f.write(markdown_content)
                    
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
            
            logger.info(f"Exported {len(content_map)} pages to Markdown format")
            logger.info(f"Total export size: {export_results['total_size']} bytes")
            
            return export_results
            
        except Exception as e:
            error_msg = f"Error exporting to Markdown: {str(e)}"
            logger.error(error_msg)
            raise FileExportError(error_msg) from e
    
    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to Markdown with better formatting.
        
        Args:
            html: HTML content to convert
            
        Returns:
            Markdown formatted text
        """
        if not html:
            return ""
        
        try:
            # Clean up HTML first
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove HTML comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Handle code blocks with language hints
            for pre in soup.find_all('pre'):
                code = pre.find('code')
                if code:
                    # Try to determine language from class
                    language = ""
                    if code.get('class'):
                        for cls in code.get('class'):
                            if cls.startswith(('language-', 'lang-')):
                                language = cls.split('-', 1)[1]
                                break
                    
                    # If no class, try data-lang attribute
                    if not language and code.get('data-lang'):
                        language = code.get('data-lang')
                        
                    # Create a custom wrapper for the code block to ensure it gets
                    # rendered with the proper markdown syntax
                    wrapper = soup.new_tag('div')
                    wrapper['class'] = 'code-wrapper'
                    wrapper['data-language'] = language
                    
                    # Create a new opening marker with triple backticks and language
                    marker = soup.new_string(f"```{language}\n")
                    
                    # Wrap the existing code with our custom format
                    pre.wrap(wrapper)
                    code.insert_before(marker)
                    
                    # Add closing backticks after the code content
                    code.append(soup.new_string("\n```"))
            
            # Convert cleaned HTML to Markdown
            clean_html = str(soup)
            md_text = self._converter.handle(clean_html)
            
            # Fix some formatting issues
            md_text = self._post_process_markdown(md_text)
            
            return md_text
            
        except Exception as e:
            logger.warning(f"Error converting HTML to Markdown: {str(e)}")
            # Fallback to direct conversion
            return self._converter.handle(html)
    
    def _post_process_markdown(self, markdown: str) -> str:
        """
        Fix formatting issues in converted Markdown.
        
        Args:
            markdown: Initial Markdown text
            
        Returns:
            Cleaned up Markdown text
        """
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Fix backticks in code blocks (problem with some html2text versions)
        markdown = re.sub(r'```\s+```', '```', markdown)
        
        # Fix headers that might have incorrect spacing
        for i in range(6, 0, -1):
            header_marker = '#' * i
            markdown = re.sub(rf'{header_marker}([^\s#])', rf'{header_marker} \1', markdown)
        
        # Ensure backtick code blocks have proper language specification
        markdown = re.sub(r'```\s*([a-zA-Z0-9+#]+)\s*\n', r'```\1\n', markdown)
        
        # Fix lists that might have incorrect spacing
        markdown = re.sub(r'(\n[*-]\s*[^\n]+)(\n[^\s*-])', r'\1\n\2', markdown)
        
        return markdown
    
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
    
    def _make_anchor(self, text: str) -> str:
        """
        Convert text to a GitHub-compatible anchor.
        
        Args:
            text: Original text
            
        Returns:
            Anchor-compatible text
        """
        # Convert to lowercase
        anchor = text.lower()
        
        # Replace spaces with hyphens
        anchor = anchor.replace(' ', '-')
        
        # Replace special characters with hyphens
        anchor = re.sub(r'[^\w-]', '-', anchor)
        
        # Remove consecutive hyphens
        anchor = re.sub(r'-+', '-', anchor)
        
        # Remove leading/trailing hyphens
        anchor = anchor.strip('-')
        
        return anchor


class FileExportError(Exception):
    """Exception raised when file export operations fail."""
    pass
