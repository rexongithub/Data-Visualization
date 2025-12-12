"""
UI components for the Food Product Similarity Dashboard
"""
from shiny import ui
from config import DEFAULT_WEIGHTS, EDITABLE_FIELDS, COMPARISON_FIELDS, NUTRITION_FIELDS


def create_app_ui():
    """Create the main application UI with side navigation"""
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_action_button(
                "nav_data", "Data & New Entries", class_="btn btn-primary w-100 mb-1"),
            ui.input_action_button(
                "nav_similarity", "Similarity Suggestions", class_="btn btn-primary w-100 mb-1", disabled=True),
            ui.input_action_button(
                "nav_editor", "Product Editor", class_="btn btn-secondary w-100 mb-1", disabled=True),
            ui.output_ui("marked_products_indicator"),
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
            
            /* HIDE DATA GRID SUMMARY TEXT */
            .shiny-data-grid-summary {
                display: none !important;
            }
                      
            /* Truncate all cells with ellipsis */
            .shiny-data-grid td,
            .shiny-data-grid th {
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
                max-width: 0 !important;
            }
            
            /* Column widths for main data tables */
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
            
            /* Comparison panel styling */
            .comparison-panel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            
            .comparison-table {
                width: 100%;
                border-collapse: collapse;
            }
            
            .comparison-table th,
            .comparison-table td {
                padding: 8px 12px;
                border-bottom: 1px solid #dee2e6;
                text-align: left;
            }
            
            .comparison-table th {
                background-color: #e9ecef;
                font-weight: bold;
                width: 25%;
            }
            
            .comparison-table td {
                width: 37.5%;
            }
            
            .comparison-table tr:hover {
                background-color: #f1f3f5;
            }
            
            .diff-highlight {
                background-color: #fff3cd;
            }
            
            /* Clickable row styling */
            .clickable-row {
                cursor: pointer;
            }
            
            .clickable-row:hover {
                background-color: #e9ecef !important;
            }
            
            /* Badge styling */
            .badge-active {
                background-color: #28a745;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.8em;
            }
            
            .badge-inactive {
                background-color: #6c757d;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.8em;
            }
            
            /* Review card styling */
            .review-card {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
                background-color: white;
            }
            
            .review-card-active {
                border-color: #28a745;
                border-width: 2px;
            }
            
            .review-card-original {
                border-color: #007bff;
                border-width: 2px;
            }
            
            /* Editor styling */
            .editor-field {
                margin-bottom: 15px;
            }
            
            .editor-field label {
                font-weight: bold;
                display: block;
                margin-bottom: 5px;
            }
        """),
    )


def create_data_panel_content():
    """Create the Data & New Entries panel content"""
    return ui.div(
        ui.h2("Data & New Entries"),
        ui.hr(),

        ui.accordion(
            # Panel 1: Inactive Products (Open by default)
            ui.accordion_panel(
                "Inactive Products",
                ui.input_text("search_inactive", "",
                              placeholder="Search by name or brand"),
                ui.output_data_frame("inactive_products_table"),
                value="panel_inactive"  # Identifier for this panel
            ),

            # Panel 2: Active Products (Closed by default)
            ui.accordion_panel(
                "Active Products",
                ui.input_text("search_active", "",
                              placeholder="Search by name or brand"),
                ui.output_data_frame("active_products_table"),
                value="panel_active"    # Identifier for this panel
            ),
            
            id="data_accordion",
            multiple=True,  # Allows the user to have both open at the same time if they want
            open=["panel_inactive"]  # Only the inactive panel is in this list, so it starts open
        )
    )


def create_similarity_panel_content():
    """Create the Similarity Suggestions panel content"""
    return ui.div(
        ui.h2("Similarity Suggestions"),
        ui.hr(),
        ui.output_ui("similarity_section"),
    )


def create_review_panel_content():
    """Create the Review & Validation panel content"""
    return ui.div(
        ui.h2("Review & Validation"),
        ui.hr(),
        ui.output_ui("review_section"),
    )


def create_editor_panel_content():
    """Create the Product Editor panel content"""
    return ui.div(
        ui.h2("Product Editor"),
        ui.hr(),
        ui.output_ui("editor_section"),
    )


def create_product_card(product_id, product_data):
    """
    Create a card for displaying product similarity results with clickable rows

    Args:
        product_id: Product ID
        product_data: Product data Series from database

    Returns:
        Shiny UI card component
    """
    table_id = f"similarity_table_{product_id}"
    search_id = f"similarity_search_{product_id}"
    score_filter_id = f"similarity_score_filter_{product_id}"

    return ui.card(
        # Original Product Info
        ui.div(
            ui.h4(
                f"Original Product: {product_data.get('name_search', 'N/A')} (ID: {product_id})"),
            ui.span("INACTIVE", class_="badge-inactive") if product_data.get('active',
                                                                             0) == 0 else ui.span("ACTIVE", class_="badge-active"),
            class_="d-flex align-items-center gap-2 mb-3"
        ),
        ui.tags.ul(
            ui.tags.li(f"Brand: {product_data.get('brands_search', 'N/A')}"),
            ui.tags.li(f"Barcode: {product_data.get('barcode', 'N/A')}"),
            ui.tags.li(f"Energy: {product_data.get('energy', 'N/A')}"),
            ui.tags.li(f"Protein: {product_data.get('protein', 'N/A')} g"),
            ui.tags.li(f"Fat: {product_data.get('fat', 'N/A')} g"),
        ),
        ui.hr(),

        # Action buttons row
        ui.div(
            ui.input_action_button(
                f"go_to_review_{product_id}",
                "📋 Go to Review & Validation",
                class_="btn btn-success me-2"
            ),
            class_="mb-3"
        ),

        ui.h5("Similar Products (Click row to compare)"),
        ui.p("Click on a row to expand comparison view",
             class_="text-muted small"),

        # Filters
        ui.div(
            ui.row(
                ui.column(
                    6,
                    ui.input_text(
                        search_id,
                        "",
                        placeholder="Search by name or brand..."
                    )
                ),
                ui.column(
                    6,
                    ui.input_numeric(
                        score_filter_id,
                        "Minimum Score:",
                        value=0.0,
                        min=0.0,
                        max=1.0,
                        step=0.05
                    )
                )
            ),
            class_="mb-3"
        ),

        # Similarity results table
        ui.output_data_frame(table_id),

        # Comparison panel (dynamic)
        ui.output_ui(f"comparison_panel_{product_id}"),

        class_="mb-4 p-3 border rounded shadow-sm",
    )


def create_comparison_panel(original_product, similar_product, comparison_fields, is_marked=False, similar_id=None):
    """
    Create a comparison panel showing two products side by side

    Args:
        original_product: Original product data (Series or dict)
        similar_product: Similar product data (Series or dict)
        comparison_fields: List of fields to compare
        is_marked: Whether this product is already marked for review
        similar_id: ID of the similar product (for button IDs)

    Returns:
        Shiny UI component
    """
    # Create table rows
    rows = []
    for field in comparison_fields:
        orig_val = original_product.get(field, 'N/A')
        sim_val = similar_product.get(field, 'N/A')

        # Format values
        if orig_val is None or (isinstance(orig_val, float) and str(orig_val) == 'nan'):
            orig_val = 'N/A'
        if sim_val is None or (isinstance(sim_val, float) and str(sim_val) == 'nan'):
            sim_val = 'N/A'

        # Check if values are different for highlighting
        diff_class = "diff-highlight" if str(orig_val) != str(sim_val) else ""

        # Format field name nicely
        field_display = field.replace('_', ' ').title()

        rows.append(
            ui.tags.tr(
                ui.tags.th(field_display),
                ui.tags.td(str(orig_val)),
                ui.tags.td(str(sim_val), class_=diff_class),
            )
        )

    # Use provided similar_id or get from product
    if similar_id is None:
        similar_id = similar_product.get('id', 'N/A')
    is_active = similar_product.get('active', 0) == 1

    # Create appropriate button based on marked status
    if is_marked:
        action_button = ui.input_action_button(
            f"unmark_btn_{similar_id}",
            "✕ Remove from Review",
            class_="btn btn-outline-danger mt-3"
        )
        status_badge = ui.span("✓ MARKED FOR REVIEW",
                               class_="badge bg-primary ms-2")
    else:
        action_button = ui.input_action_button(
            f"mark_btn_{similar_id}",
            "Mark for Review",
            class_="btn btn-primary mt-3"
        )
        status_badge = ""

    return ui.div(
        ui.div(
            ui.h5("📊 Product Comparison"),
            class_="d-flex align-items-center gap-2 mb-3"
        ),
        ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("Field"),
                    ui.tags.th("Original Product"),
                    ui.tags.th("Similar Product"),
                )
            ),
            ui.tags.tbody(*rows),
            class_="comparison-table"
        ),
        ui.div(
            action_button,
        ),
        class_="comparison-panel mt-3"
    )


def create_review_card(product_data, is_original=False, is_active=False):
    """
    Create a card for a product in the review section

    Args:
        product_data: Product data (Series or dict)
        is_original: Whether this is the original product
        is_active: Whether this product is active

    Returns:
        Shiny UI component
    """
    product_id = product_data.get('id', 'N/A')
    card_class = "review-card"
    if is_original:
        card_class += " review-card-original"
    elif is_active:
        card_class += " review-card-active"

    badge = None
    if is_original:
        badge = ui.span("ORIGINAL", class_="badge bg-primary me-2")
    if is_active:
        badge = ui.span("ACTIVE", class_="badge bg-success me-2") if not badge else ui.span(
            ui.span("ORIGINAL", class_="badge bg-primary me-1"),
            ui.span("ACTIVE", class_="badge bg-success"),
        )
    elif not is_original:
        badge = ui.span("INACTIVE", class_="badge bg-secondary me-2")

    return ui.div(
        ui.div(
            ui.strong(f"{product_data.get('name_search', 'N/A')}"),
            " ",
            badge if badge else "",
            ui.span(f" (ID: {product_id})", class_="text-muted"),
            class_="mb-2"
        ),
        ui.tags.ul(
            ui.tags.li(f"Brand: {product_data.get('brands_search', 'N/A')}"),
            ui.tags.li(f"Barcode: {product_data.get('barcode', 'N/A')}"),
            class_="small mb-2"
        ),
        ui.input_action_button(
            f"remove_from_review_{product_id}",
            "✕ Remove",
            class_="btn btn-sm btn-outline-danger"
        ) if not is_original else "",
        class_=card_class
    )


def create_editor_form(product_data, editable_fields):
    """
    Create an editor form for a product

    Args:
        product_data: Product data (Series or dict)
        editable_fields: List of fields that can be edited

    Returns:
        Shiny UI component
    """
    product_id = product_data.get('id', 'N/A')

    form_fields = []
    for field in editable_fields:
        current_value = product_data.get(field, '')
        if current_value is None or (isinstance(current_value, float) and str(current_value) == 'nan'):
            current_value = ''

        field_display = field.replace('_', ' ').title()

        # Use numeric input for nutrition fields
        if field in NUTRITION_FIELDS:
            form_fields.append(
                ui.div(
                    ui.input_numeric(
                        f"editor_{field}",
                        field_display,
                        value=float(current_value) if current_value and str(
                            current_value) != 'nan' else None,
                        min=0,
                        step=0.1
                    ),
                    class_="editor-field"
                )
            )
        else:
            form_fields.append(
                ui.div(
                    ui.input_text(
                        f"editor_{field}",
                        field_display,
                        value=str(current_value) if current_value else ""
                    ),
                    class_="editor-field"
                )
            )

    return ui.card(
        ui.h4(f"Editing Product ID: {product_id}"),
        ui.p(f"Current Status: {'Active' if product_data.get('active', 0) == 1 else 'Inactive'}",
             class_="text-muted"),
        ui.hr(),
        ui.row(
            ui.column(6, *form_fields[:len(form_fields)//2 + 1]),
            ui.column(6, *form_fields[len(form_fields)//2 + 1:]),
        ),
        ui.hr(),
        ui.div(
            ui.input_action_button(
                "save_product_changes",
                "💾 Save Changes & Activate",
                class_="btn btn-success btn-lg me-2"
            ),
        ),
        class_="p-4"
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
        ui.tags.code("python similar_food_api.py"),
        class_="alert alert-warning"
    )


def create_no_selection_card():
    """Create a card for when no products are selected"""
    return ui.card("No product selected. Select a row from the Data & New Entries tab.")


def create_success_message(message):
    """Create a success alert message"""
    return ui.div(
        ui.h5("✓ Success"),
        ui.p(message),
        class_="alert alert-success"
    )


def create_error_message(message):
    """Create an error alert message"""
    return ui.div(
        ui.h5("✕ Error"),
        ui.p(message),
        class_="alert alert-danger"
    )


def create_info_message(message):
    """Create an info alert message"""
    return ui.div(
        ui.p(message),
        class_="alert alert-info"
    )
