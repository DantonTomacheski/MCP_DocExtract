"""
Main Controller for Documentation Scraper Python

This module contains the MainController class, which orchestrates
the entire scraping process and handles the dynamic selection of strategies.
"""

import os
import json
import uuid
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from src.extractors.interfaces import IContentExtractor, ILinkExtractor
from src.exporters.interfaces import IFileExporter
from src.services.sequential_service import SequentialScraperService
# To be implemented later
# from src.services.parallel_service import ParallelScraperService
from src.ai.content_processor import AIContentProcessor
from src.ai.link_filter import AILinkFilter

# Import specific implementations
from src.extractors.content.generic import GenericContentExtractor
from src.extractors.links.generic import GenericLinkExtractor
from src.exporters.json_exporter import JSONExporter
from src.exporters.markdown_exporter import MarkdownExporter

from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class MainController:
    """
    Main controller for the Documentation Scraper.
    
    This class orchestrates the entire scraping process, including:
    - Selecting appropriate strategies based on the mode
    - Initializing services
    - Managing the scraping process
    - Handling results and exports
    """
    
    def __init__(self):
        """Initialize the main controller."""
        # These will be initialized based on mode and configuration
        self.content_extractor = GenericContentExtractor()
        self.link_extractor = GenericLinkExtractor()
        # Initialize the scraper service with the extractors
        self.scraper_service = SequentialScraperService(
            content_extractor=self.content_extractor,
            link_extractor=self.link_extractor
        )
        self.file_exporters = [JSONExporter(), MarkdownExporter()]
        self.ai_processor = None
        self.ai_link_filter = None
        
        # Track active operations
        self.operations = {}
        
        # Default output directory
        self.default_output_dir = os.environ.get("DOC_EXTRACT_OUTPUT_DIR", "./output")
    
    def run(
        self,
        url: str,
        mode: str = "auto", 
        output_dir: Optional[str] = None,
        parallel: bool = False,
        concurrency: int = 3,
        max_depth: int = 5,
        use_ai: bool = False,
        export_format: str = "both"
    ) -> Dict[str, Any]:
        """
        Run the scraping process for a given URL.
        
        Args:
            url: URL of the documentation site to scrape
            mode: Scraping mode (generic, deepwiki, auto)
            output_dir: Directory to save output files (default: self.default_output_dir)
            parallel: Whether to use parallel processing
            concurrency: Number of concurrent workers
            max_depth: Maximum depth of links to follow
            use_ai: Whether to use AI for content processing
            export_format: Format to export (json, markdown, both)
            
        Returns:
            Dictionary with results of the scraping operation
        """
        # Use default output directory if none provided
        if output_dir is None:
            output_dir = self.default_output_dir
            
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Starting scraping process for URL: {url}")
        logger.info(f"Mode: {mode}, Parallel: {parallel}, UseAI: {use_ai}")
        
        # Create unique operation ID
        operation_id = f"ex_{uuid.uuid4().hex[:12]}"
        
        try:
            # Select appropriate extractors based on mode
            self._select_extractors(mode)
            
            # Initialize scraper service
            self._initialize_scraper_service(parallel, concurrency, max_depth, use_ai)
            
            # Initialize file exporters
            self._initialize_exporters(export_format)
            
            # Record operation
            self.operations[operation_id] = {
                "type": "extraction",
                "url": url,
                "mode": mode,
                "status": "running",
                "started_at": datetime.now(),
                "updated_at": datetime.now(),
                "progress": 0.0,
                "urls_discovered": 0,
                "urls_processed": 0,
                "output_dir": output_dir,
                "export_format": export_format
            }
            
            # Run the scraping process synchronously
            loop = asyncio.get_event_loop()
            scrape_result = loop.run_until_complete(
                self._run_scraping(operation_id, url, output_dir)
            )
            
            # Update operation with success
            self.operations[operation_id].update({
                "status": "completed",
                "updated_at": datetime.now(),
                "progress": 100.0,
                "urls_discovered": scrape_result.get("stats", {}).get("urls_discovered", 0),
                "urls_processed": scrape_result.get("stats", {}).get("urls_processed", 0),
                "message": "Scraping completed successfully",
                "exports": scrape_result.get("exports", [])
            })
            
            # Return results
            return {
                "operation_id": operation_id,
                "status": "completed",
                "message": "Scraping completed successfully",
                "url_count": scrape_result.get("stats", {}).get("urls_processed", 0),
                "exports": scrape_result.get("exports", [])
            }
            
        except Exception as e:
            logger.error(f"Error in scraping process: {str(e)}")
            
            # Update operation with failure
            self.operations[operation_id].update({
                "status": "failed",
                "updated_at": datetime.now(),
                "message": f"Error: {str(e)}"
            })
            
            # Return error results
            return {
                "operation_id": operation_id,
                "status": "failed",
                "message": f"Scraping failed: {str(e)}"
            }
    
    async def async_run(
        self,
        url: str,
        mode: str = "auto", 
        output_dir: Optional[str] = None,
        parallel: bool = False,
        concurrency: int = 3,
        max_depth: int = 5,
        use_ai: bool = False,
        export_format: str = "both"
    ) -> Dict[str, Any]:
        """
        Async version of the run method for use in MCP server.
        
        Args:
            Same as run method
            
        Returns:
            Dictionary with results or operation status
        """
        # Use default output directory if none provided
        if output_dir is None:
            output_dir = self.default_output_dir
            
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create unique operation ID
        operation_id = f"ex_{uuid.uuid4().hex[:12]}"
        
        try:
            # Select appropriate extractors based on mode
            self._select_extractors(mode)
            
            # Initialize scraper service
            self._initialize_scraper_service(parallel, concurrency, max_depth, use_ai)
            
            # Initialize file exporters
            self._initialize_exporters(export_format)
            
            # Record operation
            self.operations[operation_id] = {
                "type": "extraction",
                "url": url,
                "mode": mode,
                "status": "running",
                "started_at": datetime.now(),
                "updated_at": datetime.now(),
                "progress": 0.0,
                "urls_discovered": 0,
                "urls_processed": 0,
                "output_dir": output_dir,
                "export_format": export_format
            }
            
            # Start the scraping process asynchronously
            asyncio.create_task(
                self._run_scraping(operation_id, url, output_dir)
            )
            
            # Return initial status
            return {
                "operation_id": operation_id,
                "status": "running",
                "message": "Scraping operation started"
            }
            
        except Exception as e:
            logger.error(f"Error starting async scraping process: {str(e)}")
            
            # Record operation with error
            self.operations[operation_id] = {
                "type": "extraction",
                "url": url,
                "mode": mode,
                "status": "failed",
                "started_at": datetime.now(),
                "updated_at": datetime.now(),
                "message": f"Failed to start: {str(e)}"
            }
            
            # Return error status
            return {
                "operation_id": operation_id,
                "status": "failed",
                "message": f"Failed to start scraping: {str(e)}"
            }
        
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Get the status of an operation.
        
        Args:
            operation_id: ID of the operation to check
            
        Returns:
            Dictionary with operation status
            
        Raises:
            KeyError: If operation_id is not found
        """
        if operation_id not in self.operations:
            raise KeyError(f"Operation {operation_id} not found")
        
        # Get the base operation data
        operation = self.operations[operation_id]
        
        # If the scraper service is active, get real-time status
        if (operation["status"] == "running" and 
            self.scraper_service is not None and 
            hasattr(self.scraper_service, "get_status")):
            
            # Get status from scraper service
            try:
                # Get the status asynchronously
                loop = asyncio.get_event_loop()
                status = loop.run_until_complete(self.scraper_service.get_status())
                
                # Update operation with latest status
                operation.update({
                    "progress": status["progress_percent"],
                    "urls_discovered": status["urls_discovered"],
                    "urls_processed": status["urls_processed"],
                    "updated_at": datetime.now()
                })
                
                # If scraping is complete, but operation status hasn't been updated
                if status["is_complete"] and operation["status"] == "running":
                    operation["status"] = "processing_complete"
                    operation["message"] = "Scraping completed, processing results"
            except Exception as e:
                logger.warning(f"Error getting status from scraper service: {str(e)}")
        
        return operation
        
    def _select_extractors(self, mode: str) -> None:
        """
        Select appropriate content and link extractors based on the mode.
        
        Args:
            mode: Extraction mode (generic, deepwiki, auto)
        """
        logger.info(f"Selecting extractors for mode: {mode}")
        
        # For now, we only have generic extractors
        if mode == "generic" or mode == "auto":
            self.content_extractor = GenericContentExtractor()
            self.link_extractor = GenericLinkExtractor()
        elif mode == "deepwiki":
            # TODO: Implement DeepWiki-specific extractors
            # For now, fall back to generic
            logger.warning("DeepWiki extractors not implemented, using generic extractors")
            self.content_extractor = GenericContentExtractor()
            self.link_extractor = GenericLinkExtractor()
        else:
            raise ValueError(f"Unsupported extraction mode: {mode}")
            
        logger.debug(f"Selected content extractor: {self.content_extractor.__class__.__name__}")
        logger.debug(f"Selected link extractor: {self.link_extractor.__class__.__name__}")
        
    def _initialize_scraper_service(self, parallel: bool, concurrency: int, max_depth: int, use_ai: bool) -> None:
        """
        Initialize the appropriate scraper service based on the parallel flag.

        Args:
            parallel: Whether to use parallel processing
            concurrency: Number of concurrent workers
            max_depth: Maximum depth of links to follow
            use_ai: Whether to use AI for content processing
        """
        # First initialize AI components if requested
        if use_ai:
            try:
                logger.info("Initializing AI components for content processing and link filtering")
                # Initialize AI content processor with optimized batch size and caching
                self.ai_processor = AIContentProcessor(
                    model="gpt-4.1-nano",  # Use the specified model
                    temperature=0.0,       # Use deterministic responses
                    batch_size=10,         # Optimize batch size for efficiency
                    max_tokens=2048,       # Set reasonable token limit
                    cache_dir=os.path.join(self.default_output_dir, ".cache", "ai")
                )
                
                # Initialize AI link filter with relevance threshold
                self.ai_link_filter = AILinkFilter(
                    model="gpt-4.1-nano",     # Use the specified model
                    temperature=0.0,          # Use deterministic responses
                    batch_size=20,            # Process more links in a batch
                    cache_dir=os.path.join(self.default_output_dir, ".cache", "ai"),
                    relevance_threshold=0.7   # Only include highly relevant links
                )
                
                logger.info("AI components initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AI components: {str(e)}")
                logger.warning("Continuing without AI capabilities")
                self.ai_processor = None
                self.ai_link_filter = None
        else:
            # Reset AI components if not using AI
            self.ai_processor = None
            self.ai_link_filter = None
        
        # Then initialize the appropriate scraper service
        if not parallel:
            logger.info("Initializing sequential scraper service")
            self.scraper_service = SequentialScraperService(
                content_extractor=self.content_extractor,
                link_extractor=self.link_extractor,
                max_depth=max_depth,
                ai_processor=self.ai_processor,
                ai_link_filter=self.ai_link_filter
            )
        else:
            logger.info(f"Initializing parallel scraper service with concurrency {concurrency}")
            # TODO: Implement parallel service
            # For now, use sequential service with a warning
            logger.warning("Parallel service not implemented, using sequential")
            self.scraper_service = SequentialScraperService(
                content_extractor=self.content_extractor,
                link_extractor=self.link_extractor,
                max_depth=max_depth,
                ai_processor=self.ai_processor,
                ai_link_filter=self.ai_link_filter,
                # Use a higher rate limit to simulate parallel performance
                rate_limit=0.2
            )
        
    def _initialize_exporters(self, export_format: str) -> None:
        """
        Initialize file exporters based on the requested format.
        
        Args:
            export_format: Format to export (json, markdown, both)
        """
        self.file_exporters = []
        
        if export_format == "json" or export_format == "both":
            logger.info("Adding JSON exporter")
            self.file_exporters.append(JSONExporter())
            
        if export_format == "markdown" or export_format == "both":
            logger.info("Adding Markdown exporter")
            self.file_exporters.append(MarkdownExporter())
            
        if not self.file_exporters:
            raise ValueError(f"Unsupported export format: {export_format}")
            
        logger.debug(f"Initialized {len(self.file_exporters)} exporters")
    
    async def _run_scraping(self, operation_id: str, url: str, output_dir: str) -> Dict[str, Any]:
        """
        Run the scraping process and handle exports.
        
        Args:
            operation_id: Operation ID for tracking
            url: URL to scrape
            output_dir: Directory to save output files
            
        Returns:
            Dictionary with scraping and export results
        """
        try:
            # Start the scraping process
            logger.info(f"Starting scraping for operation {operation_id}")
            scraping_results = await self.scraper_service.scrape(url, operation_id)
            
            # Create result directory if needed
            operation_dir = os.path.join(output_dir, operation_id)
            os.makedirs(operation_dir, exist_ok=True)
            
            # Get sanitized project name from URL
            parsed_url = urlparse(url)
            domain_parts = parsed_url.netloc.split('.')
            project_name = domain_parts[0] if domain_parts[0] != 'www' else domain_parts[1]
            project_name = project_name.capitalize()
            
            # Add metadata
            metadata = {
                "operation_id": operation_id,
                "url": url,
                "start_time": self.operations[operation_id]["started_at"].isoformat(),
                "end_time": datetime.now().isoformat(),
                "stats": scraping_results.get("stats", {})
            }
            
            # Save content map to disk
            content_map_path = os.path.join(operation_dir, "content_map.json")
            with open(content_map_path, "w", encoding="utf-8") as f:
                json.dump(scraping_results["content_map"], f, indent=2)
            
            logger.info(f"Content map saved to {content_map_path}")
            
            # Run exporters
            exports = []
            for exporter in self.file_exporters:
                try:
                    logger.info(f"Running {exporter.format} exporter")
                    export_result = await exporter.export(
                        content_map=scraping_results["content_map"],
                        output_dir=operation_dir,
                        project_name=project_name,
                        metadata=metadata
                    )
                    exports.append(export_result)
                    logger.info(f"Export to {exporter.format} completed successfully")
                except Exception as e:
                    logger.error(f"Error during {exporter.format} export: {str(e)}", exc_info=True)
                    exports.append({
                        "format": exporter.format,
                        "success": False,
                        "error": str(e)
                    })
            
            # Save operation details
            operation_info_path = os.path.join(operation_dir, "operation_info.json")
            with open(operation_info_path, "w", encoding="utf-8") as f:
                json.dump(self.operations[operation_id], f, indent=2)
                
            logger.info(f"Operation info saved to {operation_info_path}")
            
            # Return combined results
            return {
                "operation_id": operation_id,
                "stats": scraping_results.get("stats", {}),
                "exports": exports,
                "content_map_path": content_map_path,
                "operation_info_path": operation_info_path
            }
            
        except Exception as e:
            logger.error(f"Error in scraping process for operation {operation_id}: {str(e)}", exc_info=True)
            
            # Update operation with error
            self.operations[operation_id].update({
                "status": "failed",
                "updated_at": datetime.now(),
                "message": f"Error: {str(e)}"
            })
            
            # Re-raise for higher-level handling
            raise
