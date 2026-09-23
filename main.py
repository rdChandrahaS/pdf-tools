from src.config import get_current_directory
from src.controllers.converter_controller import handle_image_to_pdf_ui
from src.controllers.merge_controller import handle_merge_ui
from src.logger import logger, setup_logging

import questionary


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
        print("=" * 45)

        choice = questionary.select(
            "Choose the operation:",
            choices=[
                "Image -> PDF",
                "Merge PDF",
                "Exit",
            ],
        ).ask()

        if choice == "Image -> PDF":
            handle_image_to_pdf_ui(current_directory)

        elif choice == "Merge PDF":
            handle_merge_ui(current_directory)

        elif choice == "Exit" or choice is None:
            logger.info("Exiting pdf-tools. Goodbye!")
            return


if __name__ == "__main__":
    main()