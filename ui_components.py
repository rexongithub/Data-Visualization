"""
UI components for the Food Product Similarity Dashboard
"""
from shiny import ui
from config import DEFAULT_WEIGHTS


def create_app_ui():
    """Create the main application UI with side navigation"""
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Navigation"),
            ui.input_action_button("nav_data", "Data & New Entries", class_="btn btn-primary w-100 mb-2"),
            ui.input_action_button("nav_similarity", "Similarity Suggestions", class_="btn btn-primary w-100 mb-2"),
            ui.input_action_button("nav_review", "Review & Validation", class_="btn btn-primary w-100 mb-2"),
            width="250px",
            bg="#f8f9fa"
        ),
        ui.output_ui("main_content"),
        ui.tags.style("""
            /* Force fixed table layout for all data grids */
            .shiny-data-grid table {
                table-layout: fixed !important;
                width: 100% !important;
            }
            
            /* Truncate all cells with ellipsis */
            .shiny-data-grid td,
            .shiny-data-grid th {
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
                max-width: 0 !important;
            }
            
            /* Column widths for main data tables (7 columns: id, name, brands, barcode, energy, protein, fat) */
            .shiny-data-grid td:nth-child(1),
            .shiny-data-grid th:nth-child(1) {
                width: 60px !important;
                max-width: 60px !important;
            }
            
            .shiny-data-grid td:nth-child(2),
            .shiny-data-grid th:nth-child(2) {
                width: 200px !important;
                max-width: 200px !important;
            }
            
            .shiny-data-grid td:nth-child(3),
            .shiny-data-grid th:nth-child(3) {
                width: 130px !important;
                max-width: 130px !important;
            }
            
            .shiny-data-grid td:nth-child(4),
            .shiny-data-grid th:nth-child(4) {
                width: 120px !important;
                max-width: 120px !important;
            }
            
            .shiny-data-grid td:nth-child(5),
            .shiny-data-grid th:nth-child(5) {
                width: 70px !important;
                max-width: 70px !important;
            }
            
            .shiny-data-grid td:nth-child(6),
            .shiny-data-grid th:nth-child(6) {
                width: 70px !important;
                max-width: 70px !important;
            }
            
            .shiny-data-grid td:nth-child(7),
            .shiny-data-grid th:nth-child(7) {
                width: 70px !important;
                max-width: 70px !important;
            }
            
            .shiny-data-grid td:nth-child(8),
            .shiny-data-grid th:nth-child(8) {
                width: 70px !important;
                max-width: 70px !important;
            }
            
            .shiny-data-grid td:nth-child(9),
            .shiny-data-grid th:nth-child(9) {
                width: 70px !important;
                max-width: 70px !important;
            }
        """),
        title="Food Product Similarity Dashboard",
    )


def create_data_panel_content():
    """Create the Data & New Entries panel content"""
    return ui.div(
        ui.h2("Data & New Entries"),
        ui.hr(),
        
        # Active Products Section
        ui.h4("Active Products"),
        ui.input_text("search_active", "", placeholder="Search by name or brands..."),
        ui.output_data_frame("active_products_table"),
        
        ui.br(),
        ui.br(),
        
        # Inactive Products Section
        ui.h4("Inactive Products"),
        ui.input_text("search_inactive", "", placeholder="Search by name or brands..."),
        ui.output_data_frame("inactive_products_table"),
    )


def create_similarity_panel_content():
    """Create the Similarity Suggestions panel content"""
    return ui.div(
        ui.h2("Similarity Suggestions"),
        ui.hr(),
        ui.output_ui("similarity_section"),
    )


def create_review_panel_content():
    """Create the Review & Validation panel content (WIP)"""
    return ui.div(
        ui.h2("Review & Validation"),
        ui.hr(),
        ui.p("This section is still under development.", class_="text-muted"),
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
            ui.tags.li(f"Brand: {product_data.get('brands', 'N/A')}"),
            ui.tags.li(f"Barcode: {product_data.get('barcode', 'N/A')}"),
            ui.tags.li(f"Active: {'Yes' if product_data.get('active', 0) == 1 else 'No'}"),
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
        ui.output_data_frame(table_id),
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
    return ui.card("No product selected. Select a row from the Data & New Entries tab.")