import logging
import sys

# Configure the format: Time | Level | Message
# Note: In a real production app, we might use JSON formatting here.
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

def get_logger(name: str):
    logger = logging.getLogger(name)
    
    # Only configure if not already configured to avoid duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console Handler (prints to Docker/Terminal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)
    
    return logger

# Create a global instance for easy import
logger = get_logger("indoor_network_app")
