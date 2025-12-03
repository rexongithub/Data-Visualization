"""
Server logic for the Food Product Similarity Dashboard
"""
from shiny import render, reactive
import pandas as pd
from database import DatabaseManager
from api_client import SimilarityAPIClient
from ui_components import (
    create_product_card,
    create_api_warning_card,
    create_no_selection_card
)
from config import SIMILARITY_API_URL


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
    created_handlers = set()
    
    # ----------------------
    # Helper Functions
    # ----------------------
    
    def get_filtered_data():
        """Get filtered product data based on active filter"""
        return db.get_filtered_products(input.active_filter())
    
    def get_current_weights():
        """Get current weight values from inputs"""
        return {
            "text": input.weight_text(),
            "nutrition": input.weight_nutrition(),
            "brand": input.weight_brand(),
            "barcode": input.weight_barcode()
        }
    
    # ----------------------
    # Product Table Output
    # ----------------------
    
    @output
    @render.data_frame
    def product_table():
        return render.DataTable(get_filtered_data(), selection_mode="rows")
    
    # ----------------------
    # Track Selection
    # ----------------------
    
    @reactive.Effect
    def _track_selection():
        sel = product_table.cell_selection()
        if not sel or not sel["rows"]:
            selected_product_ids.set([])
            return
        
        df = get_filtered_data()
        ids = df.iloc[list(sel["rows"])]["id"].tolist()
        selected_product_ids.set(ids)
    
    # ----------------------
    # Weight Sum Warning
    # ----------------------
    
    @output
    @render.text
    def weight_sum_warning():
        weights = get_current_weights()
        total = sum(weights.values())
        
        if abs(total - 1.0) > 0.01:
            return f"⚠️ Weights sum to {total:.2f}, should be 1.0"
        return f"✓ Weights sum to {total:.2f}"
    
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
        for pid in selected_product_ids.get():
            btn_id = f"run_similarity_{pid}"
            
            if btn_id in created_handlers:
                continue
            
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
        """Render the similarity section with product cards"""
        ids = selected_product_ids.get()
        
        if not ids:
            return create_no_selection_card()
        
        # Check API status
        if not api_client.check_health():
            return create_api_warning_card(SIMILARITY_API_URL)
        
        # Create cards for each selected product
        cards = []
        for pid in ids:
            try:
                product_data = db.get_product_by_id(pid)
                if product_data is None:
                    continue
                
                # Create output for this product's similarity table
                table_id = f"similarity_table_{pid}"
                
                @output(id=table_id)
                @render.table
                def _render_table(pid=pid):
                    results = similarity_results.get()
                    if pid not in results:
                        return pd.DataFrame({
                            "Info": [f"Click 'Run Similarity' to find matches for product {pid}."]
                        })
                    return results[pid]
                
                # Create and add card
                card = create_product_card(pid, product_data)
                cards.append(card)
                
            except Exception as e:
                print(f"Error creating card for product {pid}: {str(e)}")
                continue
        
        return cards[0] if len(cards) == 1 else cards
    
    # ----------------------
    # Cleanup
    # ----------------------
    
    @reactive.Effect
    def _cleanup():
        """Cleanup database connection on session end"""
        session.on_ended(lambda: db.close())