import sys

from loguru import logger

from analyzer.config import settings

def setup_logger():
    logger.remove()

    def sensitive_data_filter(record): # hide riot key
        token_to_hide = settings.RIOT_API_KEY

        if token_to_hide and token_to_hide in record["message"]:
            record["message"] = record["message"].replace(token_to_hide, "[RIOT_KEY]")
        return True

    log_format = "<green>{time:DD-MM-YYYY HH:mm}</green>: <cyan>{name}</cyan> ||<level>{level}</level>|| {message}"

    logger.add(
        sys.stdout,
        format=log_format,
        level="INFO",
        filter=sensitive_data_filter,
        colorize=True  # Gives beautiful terminal colors automatically!
    )

    return logger