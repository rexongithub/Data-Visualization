"""
Server logic for the Food Product Similarity Dashboard
"""
from shiny import render, reactive, ui
import pandas as pd
import time
from database import DatabaseManager
from api_client import SimilarityAPIClient
from ui_components import (
    create_data_panel_content,
    create_similarity_panel_content,
    create_review_panel_content,
    create_editor_panel_content,
    create_api_warning_card,
    create_no_selection_card,
    create_comparison_panel,
    create_review_card,
    create_editor_form,
    create_success_message,
    create_error_message,
    create_info_message
)
from config import (
    SIMILARITY_API_URL,
    DEFAULT_WEIGHTS,
    COMPARISON_FIELDS,
    EDITABLE_FIELDS,
    NUTRITION_FIELDS
)


def create_server(input, output, session):
    """
    Create the server function for the Shiny app
    """
    # Initialize components
    db = DatabaseManager()
    api_client = SimilarityAPIClient(SIMILARITY_API_URL)

    # Reactive values
    similarity_results = reactive.Value({})
    selected_product_ids = reactive.Value(
        [])  # Original product (from data tab)

    # Products marked for review (dict: {product_id: product_data})
    marked_for_review = reactive.Value({})

    # Currently expanded comparison row
    expanded_comparison_id = reactive.Value(None)

    # Current panel
    current_panel = reactive.Value("data")

    # Product being edited
    editing_product_id = reactive.Value(None)

    # Status messages
    status_message = reactive.Value(None)

    # Trigger to force table refresh after DB changes
    table_refresh_trigger = reactive.Value(0)

    # Timestamp of last save operation (for cooldown - not reactive to avoid dependency issues)
    # Use list to allow modification in nested functions
    last_save_timestamp = [0]

    # Pending similarity computation (for async loading)
    pending_similarity_product = reactive.Value(None)

    # Track created handlers to avoid duplicates
    created_handlers = set()

    # Display columns for tables
    DISPLAY_COLUMNS = ["id", "name_search", "brands_search",
                       "barcode", "energy", "protein", "fat"]

    # ----------------------
    # Navigation
    # ----------------------

    @reactive.Effect
    def _toggle_nav_buttons():
        """
        Enables or disables the navigation buttons based on whether a product is selected.
        This runs every time 'selected_product_ids' changes.
        """
        ids = selected_product_ids.get()
        is_selected = bool(ids and len(ids) > 0)

        # Enable/Disable the navigation buttons
        ui.update_action_button(
            "nav_similarity",
            disabled=not is_selected
        )
        ui.update_action_button(
            "nav_review",
            disabled=not is_selected
        )
        ui.update_action_button(
            "nav_editor",
            disabled=not is_selected
        )

        # Additionally, if a product is deselected, reset the editing product ID
        if not is_selected:
            editing_product_id.set(None)
            expanded_comparison_id.set(None)

    @reactive.Effect
    @reactive.event(input.nav_data)
    def _nav_to_data():
        current_panel.set("data")
        status_message.set(None)

    @reactive.Effect
    @reactive.event(input.nav_similarity)
    def _nav_to_similarity():
        current_panel.set("similarity")
        status_message.set(None)

    @reactive.Effect
    @reactive.event(input.nav_review)
    def _nav_to_review():
        current_panel.set("review")
        status_message.set(None)

    @reactive.Effect
    @reactive.event(input.nav_editor)
    def _nav_to_editor():
        # Sync editing_product_id with the currently selected product
        ids = selected_product_ids.get()
        if ids:
            editing_product_id.set(ids[0])
        current_panel.set("editor")
        status_message.set(None)

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
        elif panel == "editor":
            return create_editor_panel_content()
        else:
            return create_data_panel_content()

    # ----------------------
    # Sidebar indicator for marked products
    # ----------------------

    @output
    @render.ui
    def marked_products_indicator():
        marked = marked_for_review.get()
        count = len(marked)
        if count > 1:
            return ui.div(
                ui.hr(),
                ui.p(f"📌 {count - 1} product(s) marked",
                     class_="text-success fw-bold small"),
                ui.input_action_button(
                    "quick_go_review",
                    "Review and validate",
                    class_="btn btn-sm btn-outline-success w-100"
                )
            )
        return ui.p("", class_="text-muted small")

    @reactive.Effect
    @reactive.event(input.quick_go_review)
    def _quick_go_review():
        current_panel.set("review")

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
        # Depend on refresh trigger to update after DB changes
        _ = table_refresh_trigger.get()
        search = input.search_active() if hasattr(input, 'search_active') else ""
        df = get_filtered_data("1", search)
        return render.DataTable(
            df,
            selection_mode="none",
            height="70vh",
            width="100%"
        )

    # ----------------------
    # Inactive Products Table
    # ----------------------

    @output
    @render.data_frame
    def inactive_products_table():
        # Depend on refresh trigger to update after DB changes
        trigger_val = table_refresh_trigger.get()
        print(
            f"DEBUG inactive_products_table: rendering with trigger={trigger_val}")
        search = input.search_inactive() if hasattr(input, 'search_inactive') else ""
        df = get_filtered_data("0", search)
        print(
            f"DEBUG inactive_products_table: got {len(df)} inactive products")
        return render.DataTable(
            df,
            selection_mode="row",
            height="70vh",
            width="100%"
        )

    # ----------------------
    # Track Selection from Inactive Products
    # ----------------------

    @reactive.Effect
    def _track_inactive_selection():
        """Track selection from inactive products table and auto-navigate to similarity tab"""
        try:
            if current_panel.get() != "data":
                return

            # Check if we're within the cooldown period after a save (1 second)
            # This prevents auto-navigation when returning from editor
            if time.time() - last_save_timestamp[0] < 1.0:
                print(f"Skipping auto-navigation (cooldown active)")
                return

            sel = inactive_products_table.cell_selection()
            if sel and sel["rows"]:
                search = input.search_inactive() if hasattr(input, 'search_inactive') else ""
                df = get_filtered_data("0", search)

                if df.empty:
                    return

                row_idx = list(sel["rows"])[0]

                # Make sure row index is valid
                if row_idx >= len(df):
                    return

                product_id = int(df.iloc[row_idx]["id"])

                current_ids = selected_product_ids.get()
                if current_ids and len(current_ids) > 0 and current_ids[0] == product_id:
                    return

                selected_product_ids.set([product_id])
                print(f"Selected product ID: {product_id}")

                # Reset comparison panel and marked products
                expanded_comparison_id.set(None)
                marked_for_review.set({})

                # Navigate immediately to similarity tab (show loading)
                current_panel.set("similarity")

                # Set pending similarity computation - will be picked up by similarity_section
                pending_similarity_product.set(product_id)
        except Exception as e:
            print(f"Error in inactive selection tracking: {e}")
            import traceback
            traceback.print_exc()

    # ----------------------
    # Compute Similarity
    # ----------------------

    def compute_similarity(product_id):
        """Compute similarity for a product using the API"""
        weights = get_current_weights()
        success, result = api_client.get_similar_products(product_id, weights)

        store = similarity_results.get().copy()
        store[product_id] = result
        similarity_results.set(store)

    @reactive.Effect
    def _process_pending_similarity():
        """Process pending similarity computation after navigation"""
        pid = pending_similarity_product.get()
        if pid is not None:
            # Clear the pending flag
            pending_similarity_product.set(None)
            # Compute similarity (results will update similarity_section)
            compute_similarity(pid)

    # ----------------------
    # Similarity Section UI
    # ----------------------

    @output
    @render.ui
    def similarity_section():
        """Render the similarity section with product card and results list"""
        ids = selected_product_ids.get()

        if not ids:
            return create_no_selection_card()

        if not api_client.check_health():
            return create_api_warning_card(SIMILARITY_API_URL)

        pid = ids[0]

        try:
            product_data = db.get_product_by_id(pid)

            if product_data is None:
                return ui.card(f"Product with ID {pid} not found.")

            # Get similarity results
            results = similarity_results.get()
            results_df = results.get(pid, pd.DataFrame())

            # Get current filters
            search_term = ""
            min_score = 0.0
            try:
                search_term = input.similarity_search()
            except:
                pass
            try:
                min_score = input.similarity_score_filter() or 0.0
            except:
                pass

            # Apply filters
            filtered_df = results_df.copy()
            if not filtered_df.empty and 'Error' not in filtered_df.columns:
                if search_term:
                    mask = (
                        filtered_df['Name'].str.contains(search_term, case=False, na=False) |
                        filtered_df['Brand'].str.contains(
                            search_term, case=False, na=False)
                    )
                    filtered_df = filtered_df[mask]

                if min_score > 0:
                    filtered_df['Score_num'] = filtered_df['Score'].astype(
                        float)
                    filtered_df = filtered_df[filtered_df['Score_num']
                                              >= min_score]

            # Build the UI
            return ui.div(
                # Results list (now includes inline comparison panels)
                ui.output_ui("similarity_results_list"),
            )

        except Exception as e:
            print(f"Error in similarity section: {str(e)}")
            import traceback
            traceback.print_exc()
            return ui.card(f"Error loading product: {str(e)}")

    @output
    @render.ui
    def similarity_results_list():
        """Render the list of similar products with Compare buttons and inline comparison panels"""
        ids = selected_product_ids.get()
        if not ids:
            return ui.div()

        pid = ids[0]
        results = similarity_results.get()

        if pid not in results:
            return ui.div(
                ui.div(
                    ui.tags.div(
                        class_="spinner-border text-primary me-2", role="status"),
                    ui.span("Computing similarity... This may take a moment."),
                    class_="d-flex align-items-center"
                ),
                class_="p-4"
            )

        df = results[pid].copy()

        if 'Error' in df.columns:
            return ui.card(df.iloc[0]['Error'], class_="alert alert-danger")

        if df.empty:
            return ui.card("No similar products found.", class_="p-3")

        # Apply filters
        search_term = ""
        min_score = 0.0
        try:
            search_term = input.similarity_search()
        except:
            pass
        try:
            # We assume input.similarity_score_filter is between 0.0 and 1.0
            min_score = input.similarity_score_filter() or 0.0
        except:
            pass

        if search_term:
            mask = (
                df['Name'].str.contains(search_term, case=False, na=False) |
                df['Brand'].str.contains(search_term, case=False, na=False)
            )
            df = df[mask]

        if min_score > 0:
            # Ensure the score is treated as a numeric value for filtering
            df['Score_num'] = df['Score'].astype(float)
            df = df[df['Score_num'] >= min_score]

        if df.empty:
            return ui.card("No products match your filters.", class_="p-3")

        # Get original product for comparison
        original_product = db.get_product_by_id(pid)
        original_dict = original_product.to_dict() if hasattr(
            original_product, 'to_dict') else dict(original_product)

        # Build list of product rows with inline comparison panels
        rows = []
        expanded_id = expanded_comparison_id.get()
        marked = marked_for_review.get()

        for idx, row in df.iterrows():
            similar_id = int(row['_id'])
            is_active = row['Active'] == 'Yes'
            is_expanded = expanded_id == similar_id
            is_marked = similar_id in marked

            # Calculate and format the score as a percentage (rounded to 2 digits)
            score_float = float(row['Score'])
            formatted_score = f"{round(score_float * 100, 2)}%"

            # Create handler for this row's compare button
            btn_id = f"compare_btn_{similar_id}"
            if btn_id not in created_handlers:
                created_handlers.add(btn_id)

                @reactive.Effect
                @reactive.event(input[btn_id])
                def _toggle_compare(sid=similar_id):
                    current = expanded_comparison_id.get()
                    if current == sid:
                        expanded_comparison_id.set(None)
                    else:
                        expanded_comparison_id.set(sid)

            # Row styling
            row_class = "p-3 border rounded clickable-row d-flex justify-content-between align-items-center"
            if is_expanded:
                row_class += " border-primary border-2 bg-light"
            elif is_marked:
                row_class += " border-success"

            # Use an invisible action button as a trigger when the entire row is clicked
            # The click handling logic should be implemented outside of this render function,
            # but for a cleaner look, the compare button can be embedded directly.

            # Build the row
            row_ui = ui.div(
                # LEFT SIDE: Product Info and Details
                ui.div(
                    # First line: Name, Brand, Status Badges
                    ui.div(
                        ui.strong(f"#{row['Rank']}", class_="me-2"),
                        ui.strong(row['Name'], class_="me-2"),
                        ui.strong(f"({row['Brand']})",
                                  class_="text-muted me-2"),
                        ui.span("ACTIVE", class_="badge bg-success me-1") if is_active else ui.span(
                            "INACTIVE", class_="badge bg-secondary me-1"),
                        ui.span(
                            "✓ MARKED", class_="badge bg-primary") if is_marked else "",
                        class_="d-flex align-items-center flex-wrap"
                    ),
                    class_="flex-grow-1"
                ),

                # RIGHT SIDE: Score and Compare Button
                ui.div(
                    # Score (now prominent and on the right)
                    ui.div(
                        ui.strong(formatted_score),
                        class_="fs-4 text-primary text-end mb-1"
                    ),
                    # Compare Button
                    ui.div(
                        ui.input_action_button(
                            btn_id,
                            "▲ Close" if is_expanded else "▼ Compare",
                            class_="btn btn-sm btn-outline-primary w-100"
                        ),
                        class_="mt-1"
                    ),
                    style="width: 100px; text-align: center; margin-left: 15px;"
                ),
                class_=row_class  # 'd-flex justify-content-between align-items-center' applied here
            )

            # If this row is expanded, add the comparison panel right below it
            if is_expanded:
                similar_product = db.get_product_by_id(similar_id)
                if similar_product is not None:
                    similar_dict = similar_product.to_dict() if hasattr(
                        similar_product, 'to_dict') else dict(similar_product)

                    # Create mark/unmark handlers
                    mark_btn_id = f"mark_btn_{similar_id}"
                    if mark_btn_id not in created_handlers:
                        created_handlers.add(mark_btn_id)

                        @reactive.Effect
                        @reactive.event(input[mark_btn_id])
                        def _mark_product(sid=similar_id):
                            marked = marked_for_review.get().copy()

                            # Also add original product if not already there
                            orig_ids = selected_product_ids.get()
                            if orig_ids:
                                orig_id = orig_ids[0]
                                if orig_id not in marked:
                                    orig_product = db.get_product_by_id(
                                        orig_id)
                                    if orig_product is not None:
                                        marked[orig_id] = {
                                            'data': orig_product.to_dict() if hasattr(orig_product, 'to_dict') else dict(orig_product),
                                            'is_original': True,
                                            'is_active': orig_product.get('active', 0) == 1
                                        }

                            # Add similar product
                            similar_prod = db.get_product_by_id(sid)
                            if similar_prod is not None:
                                marked[sid] = {
                                    'data': similar_prod.to_dict() if hasattr(similar_prod, 'to_dict') else dict(similar_prod),
                                    'is_original': False,
                                    'is_active': similar_prod.get('active', 0) == 1
                                }

                            marked_for_review.set(marked)
                            print(
                                f"Marked product {sid} for review. Total marked: {len(marked)}")

                    unmark_btn_id = f"unmark_btn_{similar_id}"
                    if unmark_btn_id not in created_handlers:
                        created_handlers.add(unmark_btn_id)

                        @reactive.Effect
                        @reactive.event(input[unmark_btn_id])
                        def _unmark_product(sid=similar_id):
                            marked = marked_for_review.get().copy()
                            if sid in marked:
                                del marked[sid]
                                marked_for_review.set(marked)
                                print(
                                    f"Unmarked product {sid}. Total marked: {len(marked)}")

                    comparison_ui = create_comparison_panel(
                        original_dict, similar_dict, COMPARISON_FIELDS, is_marked, similar_id)

                    # Wrap row and comparison together
                    rows.append(ui.div(
                        row_ui,
                        comparison_ui,
                        class_="mb-2"
                    ))
                else:
                    rows.append(ui.div(row_ui, class_="mb-2"))
            else:
                rows.append(ui.div(row_ui, class_="mb-2"))

        return ui.div(
            ui.p(
                f'Showing similar products for "{original_dict["name_search"]}"', class_="text-muted small"),
            *rows
        )

    # ----------------------
    # Go to Review Button Handler
    # ----------------------

    @reactive.Effect
    @reactive.event(input.go_to_review_btn)
    def _go_to_review():
        # Add original product to marked if not already
        ids = selected_product_ids.get()
        if ids:
            pid = ids[0]
            marked = marked_for_review.get().copy()
            if pid not in marked:
                product_data = db.get_product_by_id(pid)
                if product_data is not None:
                    marked[pid] = {
                        'data': product_data.to_dict() if hasattr(product_data, 'to_dict') else dict(product_data),
                        'is_original': True,
                        'is_active': product_data.get('active', 0) == 1
                    }
                    marked_for_review.set(marked)
        current_panel.set("review")

    # ----------------------
    # Review Section UI
    # ----------------------

    @output
    @render.ui
    def review_section():
        """Render the review and validation section"""
        marked = marked_for_review.get()
        msg = status_message.get()

        if not marked:
            return create_no_selection_card()

        # Show status message if any
        status_ui = None
        if msg:
            if msg.get('type') == 'success':
                status_ui = create_success_message(msg.get('text', ''))
            elif msg.get('type') == 'error':
                status_ui = create_error_message(msg.get('text', ''))
            else:
                status_ui = create_info_message(msg.get('text', ''))

        # Separate original, active, and inactive products
        original_product = None
        active_products = []
        inactive_products = []

        for pid, info in marked.items():
            if info.get('is_original'):
                original_product = (pid, info)
            elif info.get('is_active'):
                active_products.append((pid, info))
            else:
                inactive_products.append((pid, info))

        # Check for multiple active products
        error_ui = None
        if len(active_products) > 1:
            error_ui = create_error_message(
                f"You have {len(active_products)} active products marked. "
                "Please remove all but one active product before linking."
            )

        # Build the UI with remove buttons
        cards = []

        if original_product:
            pid, info = original_product
            cards.append(ui.h5("Original Product (from Data tab)"))
            cards.append(_create_review_card_with_remove(
                pid, info, is_original=True))

        if active_products:
            cards.append(
                ui.h5(f"Active Product(s) - {len(active_products)} selected", class_="mt-4"))
            for pid, info in active_products:
                cards.append(_create_review_card_with_remove(
                    pid, info, is_original=False, is_active=True))

        if inactive_products:
            cards.append(
                ui.h5(f"Inactive Products - {len(inactive_products)} selected", class_="mt-4"))
            for pid, info in inactive_products:
                cards.append(_create_review_card_with_remove(
                    pid, info, is_original=False, is_active=False))

        # Action button
        action_btn = ui.div(
            ui.hr(),
            ui.input_action_button(
                "link_products_btn",
                "🔗 Link Products",
                class_="btn btn-success btn-lg"
            ),
            ui.p(
                "This will merge barcodes and link all selected products to the active product.",
                class_="text-muted small mt-2"
            ),
            class_="mt-4"
        ) if not error_ui else ""

        return ui.div(
            status_ui if status_ui else "",
            error_ui if error_ui else "",
            *cards,
            action_btn
        )

    def _create_review_card_with_remove(pid, info, is_original=False, is_active=False):
        """Create a review card with remove button"""
        data = info['data']

        # Card styling
        card_class = "p-3 mb-2 border rounded"
        if is_original:
            card_class += " border-primary border-2"
        elif is_active:
            card_class += " border-success border-2"

        # Create remove handler
        remove_btn_id = f"remove_review_{pid}"
        if remove_btn_id not in created_handlers:
            created_handlers.add(remove_btn_id)

            @reactive.Effect
            @reactive.event(input[remove_btn_id])
            def _remove(remove_pid=pid):
                marked = marked_for_review.get().copy()
                if remove_pid in marked:
                    del marked[remove_pid]
                    marked_for_review.set(marked)
                    print(f"Removed product {remove_pid} from review")

        badges = []
        if is_original:
            badges.append(ui.span("ORIGINAL", class_="badge bg-primary me-1"))
        if is_active:
            badges.append(ui.span("ACTIVE", class_="badge bg-success me-1"))
        elif not is_original:
            badges.append(
                ui.span("INACTIVE", class_="badge bg-secondary me-1"))

        return ui.div(
            ui.div(
                ui.div(
                    ui.strong(data.get('name_search', 'N/A')),
                    " ",
                    *badges,
                    ui.span(f" (ID: {pid})", class_="text-muted"),
                ),
                ui.div(
                    ui.span(
                        f"Brand: {data.get('brands_search', 'N/A')} | ", class_="small"),
                    ui.span(
                        f"Barcode: {data.get('barcode', 'N/A')}", class_="small text-muted"),
                ),
                class_="flex-grow-1"
            ),
            ui.input_action_button(
                remove_btn_id,
                "✕ Remove",
                class_="btn btn-sm btn-outline-danger"
            ) if not is_original else "",
            class_=card_class,
            style="display: flex; align-items: center;"
        )

    @reactive.Effect
    @reactive.event(input.go_to_similarity_from_review)
    def _go_to_similarity():
        current_panel.set("similarity")

    # ----------------------
    # Link Products Handler
    # ----------------------

    @reactive.Effect
    @reactive.event(input.link_products_btn)
    def _link_products():
        """Handle the link products action"""
        marked = marked_for_review.get()

        if not marked:
            status_message.set(
                {'type': 'error', 'text': 'No products marked for review.'})
            return

        # Find original, active, and inactive products
        original_id = None
        original_data = None
        active_product_id = None
        inactive_ids = []

        for pid, info in marked.items():
            if info.get('is_original'):
                original_id = pid
                original_data = info['data']
            if info.get('is_active') and not info.get('is_original'):
                active_product_id = pid
            elif not info.get('is_active') and not info.get('is_original'):
                inactive_ids.append(pid)

        # Count active products (excluding original)
        active_count = sum(1 for pid, info in marked.items()
                           if info.get('is_active') and not info.get('is_original'))

        if active_count > 1:
            status_message.set({
                'type': 'error',
                'text': 'Multiple active products selected. Please remove all but one.'
            })
            return

        # Case 1: Active product exists - link everything to it
        if active_product_id:
            products_to_link = []
            if original_id:
                products_to_link.append(original_id)
            products_to_link.extend(inactive_ids)

            success, message = db.link_products(
                active_product_id, products_to_link)

            if success:
                status_message.set({
                    'type': 'success',
                    'text': f'Successfully linked {len(products_to_link)} products to active product {active_product_id}. '
                    f'Barcodes merged and deleted timestamps set.'
                })
                # Clear marked products and refresh tables
                marked_for_review.set({})
                table_refresh_trigger.set(table_refresh_trigger.get() + 1)
            else:
                status_message.set({'type': 'error', 'text': message})

        # Case 2: No active product but have similar products - treat original as active, go to editor
        elif inactive_ids and original_id:
            # Link inactive products to original
            success, message = db.link_products(original_id, inactive_ids)

            if success:
                status_message.set({
                    'type': 'info',
                    'text': f'Products linked to original. Now edit the original product to activate it.'
                })
                # Set up editor for original product
                editing_product_id.set(original_id)
                current_panel.set("editor")
                # Clear marked products and refresh tables
                marked_for_review.set({})
                table_refresh_trigger.set(table_refresh_trigger.get() + 1)
            else:
                status_message.set({'type': 'error', 'text': message})

        # Case 3: Only original product - go to editor
        elif original_id and not inactive_ids:
            status_message.set({
                'type': 'info',
                'text': 'No similar products selected. Opening editor to activate the original product.'
            })
            editing_product_id.set(original_id)
            current_panel.set("editor")
            marked_for_review.set({})

        else:
            status_message.set({
                'type': 'error',
                'text': 'Please select at least the original product to continue.'
            })

    # ----------------------
    # Editor Section UI
    # ----------------------

    @output
    @render.ui
    def editor_section():
        """Render the product editor section"""
        edit_id = editing_product_id.get()
        msg = status_message.get()

        # Show status message if any
        status_ui = None
        if msg:
            if msg.get('type') == 'success':
                status_ui = create_success_message(msg.get('text', ''))
            elif msg.get('type') == 'error':
                status_ui = create_error_message(msg.get('text', ''))
            else:
                status_ui = create_info_message(msg.get('text', ''))

        if not edit_id:
            # Check if there's an original product to edit
            orig_ids = selected_product_ids.get()
            if orig_ids:
                edit_id = orig_ids[0]
                editing_product_id.set(edit_id)
            else:
                return ui.div(
                    status_ui if status_ui else "",
                    create_info_message(
                        "No product selected for editing. "
                        "Select a product from the Data tab or complete the Review & Validation workflow."
                    ),
                    ui.input_action_button(
                        "go_to_data_from_editor",
                        "Go to Data & New Entries",
                        class_="btn btn-primary"
                    )
                )

        product_data = db.get_product_by_id(edit_id)
        if product_data is None:
            return ui.div(
                status_ui if status_ui else "",
                create_error_message(
                    f"Product {edit_id} not found in database.")
            )

        product_dict = product_data.to_dict() if hasattr(
            product_data, 'to_dict') else dict(product_data)

        return ui.div(
            status_ui if status_ui else "",
            create_editor_form(product_dict, EDITABLE_FIELDS)
        )

    @reactive.Effect
    @reactive.event(input.go_to_data_from_editor)
    def _go_to_data():
        current_panel.set("data")

    @reactive.Effect
    @reactive.event(input.cancel_editor)
    def _cancel_editor():
        editing_product_id.set(None)
        selected_product_ids.set([])
        marked_for_review.set({})
        status_message.set(None)
        # Set timestamp to suppress auto-navigation for 1 second
        last_save_timestamp[0] = time.time()
        # Navigate to data tab FIRST, then refresh tables
        current_panel.set("data")
        table_refresh_trigger.set(table_refresh_trigger.get() + 1)

    # ----------------------
    # Save Product Changes Handler
    # ----------------------

    @reactive.Effect
    @reactive.event(input.save_product_changes)
    def _save_product():
        """Save changes to the product and activate it"""
        edit_id = editing_product_id.get()
        if not edit_id:
            status_message.set(
                {'type': 'error', 'text': 'No product being edited.'})
            return

        # Collect field values
        updates = {}
        for field in EDITABLE_FIELDS:
            input_id = f"editor_{field}"
            try:
                value = input[input_id]()
                if value is not None and str(value).strip() != '':
                    if field in NUTRITION_FIELDS:
                        updates[field] = float(value)
                    else:
                        updates[field] = str(value)
                else:
                    updates[field] = None
            except Exception as e:
                print(f"Error getting value for {field}: {e}")

        # Check for marked products that need to be linked/deleted
        marked = marked_for_review.get()
        inactive_ids_to_link = []
        for pid, info in marked.items():
            # Find non-original inactive products that should be linked to this one
            if not info.get('is_original') and not info.get('is_active') and pid != edit_id:
                inactive_ids_to_link.append(pid)

        # If there are products to link, do it before activating
        if inactive_ids_to_link:
            link_success, link_message = db.link_products(
                edit_id, inactive_ids_to_link)
            if not link_success:
                status_message.set(
                    {'type': 'error', 'text': f'Failed to link products: {link_message}'})
                return
            print(f"Linked {len(inactive_ids_to_link)} products to {edit_id}")

        # Activate the product
        success, message = db.activate_product(edit_id, updates)

        if success:
            status_message.set({
                'type': 'success',
                'text': f'Product {edit_id} has been updated and activated successfully!'
            })
            # Reset state
            editing_product_id.set(None)
            selected_product_ids.set([])
            marked_for_review.set({})

            # Set timestamp to suppress auto-navigation for 1 second
            last_save_timestamp[0] = time.time()

            # Navigate to data tab FIRST, then refresh tables (so table is visible when trigger changes)
            current_panel.set("data")
            table_refresh_trigger.set(table_refresh_trigger.get() + 1)
        else:
            status_message.set({'type': 'error', 'text': message})

    # ----------------------
    # Cleanup
    # ----------------------

    @reactive.Effect
    def _cleanup():
        """Cleanup database connection on session end"""
        session.on_ended(lambda: db.close())
