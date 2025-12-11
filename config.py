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
    "text": 0.9,
    "nutrition": 0.03,
    "brand": 0.07,
    "barcode": 0.0
}

WEIGHT_SLIDER_CONFIG = {
    "min": 0.0,
    "max": 1.0,
    "step": 0.05
}

# Similarity Configuration
TOP_N_RESULTS = 20
API_TIMEOUT = 30

# Editor Configuration - fields that can be edited
EDITABLE_FIELDS = [
    "name_search",
    "brands_search",
    "energy",
    "protein",
    "fat",
    "saturated_fatty_acid",
    "carbohydrates",
    "sugar",
    "salt"
]

# Fields to display in comparison view
COMPARISON_FIELDS = [
    "id",
    "name_search",
    "brands_search",
    "barcode",
    "active",
    "energy",
    "protein",
    "fat",
    "saturated_fatty_acid",
    "carbohydrates",
    "sugar",
    "salt",
    "categories"
]

# Nutrition fields (numeric)
NUTRITION_FIELDS = [
    "energy",
    "protein",
    "fat",
    "saturated_fatty_acid",
    "carbohydrates",
    "sugar",
    "salt"
]
