#!/usr/bin/env python3
"""
PLCopen XML to Mermaid Converter
Main entry point for the application
"""

import logging
from gui_manager import GUIManager
from mermaid_processor import MermaidProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main function to start the application"""
    try:
        logger.info("Starting PLCopen XML to Mermaid Converter")

        # Initialize components
        gui_manager = GUIManager()
        mermaid_processor = MermaidProcessor()

        # Start the application
        gui_manager.start_application(mermaid_processor)

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise


if __name__ == "__main__":
    main()