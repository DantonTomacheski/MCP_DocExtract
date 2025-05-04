"""
Documentation Scraper Python - Main Entry Point

This is the main entry point for the Documentation Scraper Python application.
It parses command line arguments and orchestrates the scraping process.
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Optional, Any

# Import controllers and services
from src.controllers.main_controller import MainController
from src.server.mcp_server import MCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")


def setup_argparse() -> argparse.ArgumentParser:
    """
    Set up command line argument parsing.
    
    Returns:
        Configured ArgumentParser object
    """
    parser = argparse.ArgumentParser(
        description="Documentation Scraper Python - Extract and process documentation from websites"
    )
    
    # Required arguments
    parser.add_argument(
        "--url", 
        type=str,
        help="URL of the documentation site to scrape"
    )
    
    # Optional arguments
    parser.add_argument(
        "--mode",
        type=str,
        choices=["generic", "deepwiki", "auto"],
        default="auto",
        help="Scraping mode to use (default: auto)"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./output",
        help="Output directory for extracted documentation (default: ./output)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing for better performance"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Number of concurrent workers for parallel scraping (default: 3)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum depth of links to follow from the starting URL (default: 5)"
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Enable AI-powered content processing and link filtering"
    )
    
    # Server options
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start in server mode (MCP or API)"
    )
    parser.add_argument(
        "--server-type",
        type=str,
        choices=["mcp", "api", "both"],
        default="both",
        help="Server type to start (default: both)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind the server to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    
    return parser


def main():
    """
    Main entry point for the application.
    
    Parses command line arguments and starts the appropriate mode
    (scraping or server).
    """
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Start in server mode if requested
    if args.server:
        logger.info(f"Starting server in {args.server_type} mode")
        if args.server_type in ["mcp", "both"]:
            # Start MCP server
            server = MCPServer(host=args.host, port=args.port)
            server.start()
        elif args.server_type == "api":
            # This would start the API server (to be implemented)
            logger.error("API-only server mode not yet implemented")
            sys.exit(1)
        return
    
    # Validate required arguments for scraping mode
    if not args.url:
        logger.error("URL is required for scraping mode")
        parser.print_help()
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.out, exist_ok=True)
    
    # Initialize controller and run scraping
    try:
        logger.info(f"Starting scraping process for {args.url}")
        controller = MainController()
        result = controller.run(
            url=args.url,
            mode=args.mode,
            output_dir=args.out,
            parallel=args.parallel,
            concurrency=args.concurrency,
            max_depth=args.max_depth,
            use_ai=args.use_ai
        )
        logger.info(f"Scraping completed successfully: {result}")
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
