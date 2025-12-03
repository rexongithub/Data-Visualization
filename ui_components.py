"""
UI components for the Food Product Similarity Dashboard
"""
from shiny import ui
from config import DEFAULT_WEIGHTS, WEIGHT_SLIDER_CONFIG


def create_app_ui():
    """Create the main application UI"""
    return ui.page_navbar(
        create_data_panel(),
        create_similarity_panel(),
        create_review_panel(),
        title="Food Product Similarity Dashboard",
    )


def create_data_panel():
    """Create the Data & New Entries panel"""
    return ui.nav_panel(
        "Data & New Entries",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_radio_buttons(
                    "active_filter",
                    "Show Products:",
                    choices={"all": "All", "1": "Active Only", "0": "Inactive Only"},
                    selected="0",
                )
            ),
            ui.output_data_frame("product_table"),
        ),
    )


def create_similarity_panel():
    """Create the Similarity Suggestions panel"""
    return ui.nav_panel(
        "Similarity Suggestions",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("Similarity Options"),
                create_weight_sliders(),
                ui.output_text("weight_sum_warning")
            ),
            ui.output_ui("similarity_section"),
        ),
    )


def create_weight_sliders():
    """Create weight slider inputs"""
    slider_config = WEIGHT_SLIDER_CONFIG
    
    return ui.div(
        ui.input_slider(
            "weight_text",
            "Text Weight:",
            min=slider_config["min"],
            max=slider_config["max"],
            value=DEFAULT_WEIGHTS["text"],
            step=slider_config["step"]
        ),
        ui.input_slider(
            "weight_nutrition",
            "Nutrition Weight:",
            min=slider_config["min"],
            max=slider_config["max"],
            value=DEFAULT_WEIGHTS["nutrition"],
            step=slider_config["step"]
        ),
        ui.input_slider(
            "weight_brand",
            "Brand Weight:",
            min=slider_config["min"],
            max=slider_config["max"],
            value=DEFAULT_WEIGHTS["brand"],
            step=slider_config["step"]
        ),
        ui.input_slider(
            "weight_barcode",
            "Barcode Weight:",
            min=slider_config["min"],
            max=slider_config["max"],
            value=DEFAULT_WEIGHTS["barcode"],
            step=slider_config["step"]
        ),
    )


def create_review_panel():
    """Create the Review & Validation panel"""
    return ui.nav_panel(
        "Review & Validation",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_action_button("approve", "Approve Match"),
                ui.input_action_button("reject", "Reject / Create New Entry"),
            ),
            ui.output_table("review_table"),
        ),
    )


def create_product_card(product_id, product_data):
    """
    Create a card for displaying product similarity results
    
    Args:
        product_id: Product ID
        product_data: Product data Series from database
    
    Returns:
        Shiny UI card component
    """
    table_id = f"similarity_table_{product_id}"
    
    return ui.card(
        ui.h4(f"{product_data['name']} (ID: {product_id})"),
        ui.tags.ul(
            ui.tags.li(f"Category: {product_data.get('categories', 'N/A')}"),
            ui.tags.li(f"Energy: {product_data.get('energy', 'N/A')}"),
            ui.tags.li(f"Protein: {product_data.get('protein', 'N/A')} g"),
            ui.tags.li(f"Fat: {product_data.get('fat', 'N/A')} g"),
        ),
        ui.input_action_button(
            f"run_similarity_{product_id}",
            "🔍 Run Similarity",
            class_="btn btn-primary"
        ),
        ui.hr(),
        ui.h5("Similarity Results"),
        ui.output_table(table_id),
        class_="mb-4 p-3 border rounded shadow-sm",
    )


def create_api_warning_card(api_url):
    """
    Create a warning card when API is not accessible
    
    Args:
        api_url: The expected API URL
    
    Returns:
        Shiny UI card component
    """
    return ui.card(
        ui.h4("⚠️ Similarity API Not Running"),
        ui.p("The similarity API server is not running or not accessible."),
        ui.p(f"Expected URL: {api_url}"),
        ui.p("Please start the API server with:"),
        ui.tags.code("python api_similarity.py"),
        class_="alert alert-warning"
    )


def create_no_selection_card():
    """Create a card for when no products are selected"""
    return ui.card("No products selected. Select rows from the Data & New Entries tab.")