import logging
from gui_manager import GUIManager
from mermaid_processor import MermaidProcessor
from drawio_processor import DrawIOProcessor

# Configure logging - FIXED THE TYPO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # asctime NOT asasctime
    handlers=[
        logging.FileHandler('conversion.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    try:
        logger.info("Starting PLCopen XML to Diagram Converter")

        # Initialize components
        gui_manager = GUIManager()
        mermaid_processor = MermaidProcessor()
        drawio_processor = DrawIOProcessor()

        # Start application with both processors - ONLY 3 ARGUMENTS
        gui_manager.start_application(mermaid_processor, drawio_processor)

    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        raise


if __name__ == "__main__":
    main()