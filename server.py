"""
Server logic for the Food Product Similarity Dashboard
"""
from shiny import render, reactive, ui
import pandas as pd
from database import DatabaseManager
from api_client import SimilarityAPIClient
from ui_components import (
    create_data_panel_content,
    create_similarity_panel_content,
    create_review_panel_content,
    create_product_card,
    create_api_warning_card,
    create_no_selection_card
)
from config import SIMILARITY_API_URL, DEFAULT_WEIGHTS


def create_server(input, output, session):
    """
    Create the server function for the Shiny app
    
    Args:
        input: Shiny input object
        output: Shiny output object
        session: Shiny session object
    """
    # Initialize components
    db = DatabaseManager()
    api_client = SimilarityAPIClient(SIMILARITY_API_URL)
    
    # Reactive values
    similarity_results = reactive.Value({})
    selected_product_ids = reactive.Value([])
    selected_similarity_products = reactive.Value([])  # Store selected products from similarity results
    created_handlers = set()
    current_panel = reactive.Value("data")  # Track which panel is active
    
    # Display columns for tables
    DISPLAY_COLUMNS = ["id", "name", "brands", "barcode", "energy", "protein", "fat"]
    
    # Columns to display in similarity results (excluding _id which is hidden)
    SIMILARITY_DISPLAY_COLUMNS = ["Rank", "Name", "Brand", "Barcode", "Active", "Score", "Energy", "Protein", "Fat"]
    
    # ----------------------
    # Navigation
    # ----------------------
    
    @reactive.Effect
    @reactive.event(input.nav_data)
    def _nav_to_data():
        current_panel.set("data")
    
    @reactive.Effect
    @reactive.event(input.nav_similarity)
    def _nav_to_similarity():
        current_panel.set("similarity")
    
    @reactive.Effect
    @reactive.event(input.nav_review)
    def _nav_to_review():
        current_panel.set("review")
    
    @output
    @render.ui
    def main_content():
        """Render the main content based on current panel"""
        panel = current_panel.get()
        
        if panel == "data":
            return create_data_panel_content()
        elif panel == "similarity":
            return create_similarity_panel_content()
        elif panel == "review":
            return create_review_panel_content()
        else:
            return create_data_panel_content()
    
    # ----------------------
    # Helper Functions
    # ----------------------
    
    def get_filtered_data(active_status, search_term=""):
        """Get filtered product data"""
        return db.get_filtered_products(
            active_status, 
            search_term=search_term,
            columns=DISPLAY_COLUMNS
        )
    
    def get_current_weights():
        """Get current weight values (using defaults)"""
        return DEFAULT_WEIGHTS
    
    # ----------------------
    # Active Products Table
    # ----------------------
    
    @output
    @render.data_frame
    def active_products_table():
        search = input.search_active() if hasattr(input, 'search_active') else ""
        df = get_filtered_data("1", search)
        return render.DataTable(
            df, 
            selection_mode="none",
            height="300px",
            width="100%"
        )
    
    # ----------------------
    # Inactive Products Table
    # ----------------------
    
    @output
    @render.data_frame
    def inactive_products_table():
        search = input.search_inactive() if hasattr(input, 'search_inactive') else ""
        df = get_filtered_data("0", search)
        return render.DataTable(
            df, 
            selection_mode="row",
            height="300px",
            width="100%"
        )
    
    # ----------------------
    # Track Selection from Both Tables
    # ----------------------
    
    @reactive.Effect
    def _track_active_selection():
        """Track selection from active products table - NOT ALLOWED"""
        try:
            sel = active_products_table.cell_selection()
            if sel and sel["rows"]:
                # Clear any selection from active products
                # We only allow selection from inactive products
                pass
        except Exception as e:
            print(f"Error in active selection tracking: {e}")
    
    @reactive.Effect
    def _track_inactive_selection():
        """Track selection from inactive products table"""
        try:
            sel = inactive_products_table.cell_selection()
            if sel and sel["rows"]:
                search = input.search_inactive() if hasattr(input, 'search_inactive') else ""
                df = get_filtered_data("0", search)
                # Get only the first selected row (single selection)
                row_idx = list(sel["rows"])[0]
                product_id = int(df.iloc[row_idx]["id"])  # Convert to Python int
                selected_product_ids.set([product_id])
                print(f"Selected product ID: {product_id}")
        except Exception as e:
            print(f"Error in inactive selection tracking: {e}")
    
    # ----------------------
    # Compute Similarity
    # ----------------------
    
    def compute_similarity(product_id):
        """
        Compute similarity for a product using the API
        
        Args:
            product_id: ID of the product to compute similarity for
        """
        weights = get_current_weights()
        success, result = api_client.get_similar_products(product_id, weights)
        
        # Store results
        store = similarity_results.get().copy()
        store[product_id] = result
        similarity_results.set(store)
    
    # ----------------------
    # Similarity Button Handlers
    # ----------------------
    
    @reactive.Effect
    def _watch_similarity_buttons():
        """Watch for similarity button clicks and create handlers"""
        ids = selected_product_ids.get()
        if not ids:
            return
        
        pid = ids[0]  # Only one product allowed
        btn_id = f"run_similarity_{pid}"
        
        if btn_id in created_handlers:
            return
        
        created_handlers.add(btn_id)
        
        @reactive.Effect
        @reactive.event(input[btn_id])
        def _handler(pid=pid):
            compute_similarity(pid)
    
    # ----------------------
    # Similarity Section UI
    # ----------------------
    
    @output
    @render.ui
    def similarity_section():
        """Render the similarity section with product card"""
        ids = selected_product_ids.get()
        
        print(f"Similarity section - selected IDs: {ids}")
        
        if not ids:
            return create_no_selection_card()
        
        # Check API status
        if not api_client.check_health():
            return create_api_warning_card(SIMILARITY_API_URL)
        
        # Get the single selected product (only one allowed)
        pid = ids[0]
        print(f"Loading product with ID: {pid}")
        
        try:
            product_data = db.get_product_by_id(pid)
            
            if product_data is None:
                print(f"Product {pid} not found in database")
                return ui.card(f"Product with ID {pid} not found.")
            
            print(f"Product found: {product_data['name']}")
            
            # Create output for this product's similarity table
            table_id = f"similarity_table_{pid}"
            
            @output(id=table_id)
            @render.data_frame
            def _render_table(pid=pid):
                results = similarity_results.get()
                if pid not in results:
                    return render.DataTable(
                        pd.DataFrame({
                            "Info": [f"Click 'Run Similarity' to find matches for product {pid}."]
                        }),
                        selection_mode="none"
                    )
                
                # Get results and exclude the hidden _id column from display
                df = results[pid]
                display_df = df[SIMILARITY_DISPLAY_COLUMNS] if '_id' in df.columns else df
                
                return render.DataTable(
                    display_df,
                    selection_mode="rows",
                    height="400px",
                    width="100%"
                )
            
            # Track selection in similarity results table
            @reactive.Effect
            def _track_similarity_selection():
                try:
                    # Get the table output
                    table_output = output[table_id]
                    if hasattr(table_output, 'cell_selection'):
                        sel = table_output.cell_selection()
                        if sel and sel["rows"]:
                            results = similarity_results.get()
                            if pid in results:
                                df = results[pid]
                                # Get the selected rows with their IDs
                                selected_rows = []
                                for row_idx in sel["rows"]:
                                    row_data = {
                                        'id': int(df.iloc[row_idx]['_id']),
                                        'name': df.iloc[row_idx]['Name'],
                                        'brand': df.iloc[row_idx]['Brand'],
                                        'barcode': df.iloc[row_idx]['Barcode']
                                    }
                                    selected_rows.append(row_data)
                                selected_similarity_products.set(selected_rows)
                                print(f"Selected similarity products: {selected_rows}")
                except Exception as e:
                    print(f"Error tracking similarity selection: {e}")
            
            # Create and return card
            return create_product_card(pid, product_data)
            
        except Exception as e:
            print(f"Error creating card for product {pid}: {str(e)}")
            import traceback
            traceback.print_exc()
            return ui.card(f"Error loading product: {str(e)}")
    
    # ----------------------
    # Cleanup
    # ----------------------
    
    @reactive.Effect
    def _cleanup():
        """Cleanup database connection on session end"""
        session.on_ended(lambda: db.close())
    
    # ----------------------
    # Export reactive values for external access (for Review tab later)
    # ----------------------
    
    def get_selected_similarity_products():
        """
        Get the currently selected products from similarity results
        Returns: List of dicts with keys: id, name, brand, barcode
        """
        return selected_similarity_products.get()