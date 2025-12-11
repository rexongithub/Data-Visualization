"""
Food Product Similarity Dashboard - Main Application Entry Point

Features:
- Data & New Entries: Browse active/inactive products, click inactive to find similarities
- Similarity Suggestions: View similar products, click rows to compare, mark for review
- Review & Validation: Review marked products, link them together
- Product Editor: Edit and activate products

Run with: python app.py
Make sure the similarity API is running: python similar_food_api.py
"""
from shiny import App, run_app
from ui_components import create_app_ui
from server import create_server
from config import APP_HOST, APP_PORT


# Create the Shiny app
app = App(create_app_ui(), create_server)


if __name__ == "__main__":
    print("=" * 60)
    print("Food Product Similarity Dashboard")
    print("=" * 60)
    print(f"Starting server at http://{APP_HOST}:{APP_PORT}")
    print("Make sure the similarity API is running on port 5000")
    print("=" * 60)
    run_app(app, host=APP_HOST, port=APP_PORT)
