"""
Configuration settings for the Food Product Similarity Dashboard
"""

# API Configuration
SIMILARITY_API_URL = "http://localhost:5000"

# Database Configuration
DATABASE_PATH = ":memory:"
CSV_FILENAME = "view_food_clean.csv"

# App Configuration
APP_HOST = "127.0.0.1"
APP_PORT = 8000

# UI Configuration
DEFAULT_WEIGHTS = {
    "text": 0.7,
    "nutrition": 0.2,
    "brand": 0.1,
    "barcode": 0.1
}

WEIGHT_SLIDER_CONFIG = {
    "min": 0.0,
    "max": 1.0,
    "step": 0.05
}

# Similarity Configuration
TOP_N_RESULTS = 10
API_TIMEOUT = 30