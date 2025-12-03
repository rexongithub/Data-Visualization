"""
Food Product Similarity Dashboard - Main Application Entry Point
"""
from shiny import App, run_app
from ui_components import create_app_ui
from server import create_server
from config import APP_HOST, APP_PORT


# Create the Shiny app
app = App(create_app_ui(), create_server)


if __name__ == "__main__":
    run_app(app, host=APP_HOST, port=APP_PORT)