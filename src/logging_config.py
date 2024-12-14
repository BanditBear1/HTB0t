# logging_config.py
import logging
import pytz
from datetime import datetime


# Custom logging formatter to include New York timezone
class NYTzFormatter(logging.Formatter):
    def converter(self, timestamp):
        # Convert the timestamp to New York timezone
        ny_tz = pytz.timezone("America/New_York")
        dt = datetime.fromtimestamp(timestamp, tz=ny_tz)
        return dt

    def formatTime(self, record, datefmt=None):
        # Override the formatTime method to use the New York time
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)

# Create a handler if not already set (this prevents duplicate handlers in multiprocessing setups)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    # Use str.format() style formatting
    formatter = NYTzFormatter("{asctime} - {levelname} - {message}", style="{")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
