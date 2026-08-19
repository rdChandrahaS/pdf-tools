from pathlib import Path

from src.config import get_current_directory
from src.controllers.converter_controller import handle_image_to_pdf_ui
from src.controllers.merge_controller import handle_merge_ui
from src.logger import logger, setup_logging


def main() -> None:
    setup_logging()
    current_directory = get_current_directory()

    logger.info(f"Working directory: {current_directory}")
    logger.info("Starting pdf-tools...")

    while True:
        print("\n" + "=" * 45)
        print("                  pdf-tools")
        print("=" * 45)
        print(f"Current directory: {current_directory}")
        print("  [1] Image -> PDF")
        print("  [2] Merge PDF")
        print("  [0] Exit")
        print("=" * 45)

        choice = input("Choose an operation: ").strip()

        if choice == "1":
            handle_image_to_pdf_ui(current_directory)
        elif choice == "2":
            handle_merge_ui(current_directory)
        elif choice == "0":
            logger.info("Exiting pdf-tools. Goodbye!")
            return
        else:
            logger.warning("Invalid choice. Please select 1, 2, or 0.")


if __name__ == "__main__":
    main()
