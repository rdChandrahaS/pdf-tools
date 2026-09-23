import questionary

from src.config import get_current_directory
from src.controllers.compress_controller import handle_compress_ui
from src.controllers.converter_controller import handle_image_to_pdf_ui
from src.controllers.merge_controller import handle_merge_ui
from src.controllers.pdf_controller import handle_pdf_tools_ui
from src.logger import logger, setup_logging

APP_NAME = "pdf-tools"

def main() -> None:
    setup_logging()
    current_directory = get_current_directory()

    logger.info(f"Working directory: {current_directory}")
    logger.info("Starting {APP_NAME}...")

    try:
        while True:
            print("\n" + "=" * 50)
            print("                     pdf-tools")
            print("=" * 50)
            print(f"Current directory: {current_directory}")
            print("=" * 50)

            choice = questionary.select(
                "Choose an operation:",
                choices=[
                    "Image -> PDF",
                    "Merge PDF",
                    "PDF Tools",
                    "Compress PDF",
                    "Exit",
                ],
            ).ask()

            if choice == "Image -> PDF":
                handle_image_to_pdf_ui(current_directory)
            elif choice == "Merge PDF":
                handle_merge_ui(current_directory)
            elif choice == "PDF Tools":
                handle_pdf_tools_ui(current_directory)
            elif choice == "Compress PDF":
                handle_compress_ui(current_directory)
            else:
                logger.info("Exiting pdf-tools. Goodbye!")
                return
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Goodbye!")
    except EOFError:
        logger.info("Input stream closed. Goodbye!")

if __name__ == "__main__":
    main()