from shiny import App, ui, render, reactive, run_app
import pandas as pd
import duckdb
import os
import requests

# ================================
# CONFIG
# ================================
SIMILARITY_API_URL = "http://localhost:5000"

# ================================
# UI
# ================================
app_ui = ui.page_navbar(
    ui.nav_panel(
        "Data & New Entries",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_radio_buttons(
                    "active_filter",
                    "Show Products:",
                    choices={"all": "All", "1": "Active Only",
                             "0": "Inactive Only"},
                    selected="0",
                )
            ),
            ui.output_data_frame("product_table"),
        ),
    ),
    ui.nav_panel(
        "Similarity Suggestions",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("Similarity Options"),
                ui.input_slider(
                    "weight_text",
                    "Text Weight:",
                    min=0.0,
                    max=1.0,
                    value=0.7,
                    step=0.05
                ),
                ui.input_slider(
                    "weight_nutrition",
                    "Nutrition Weight:",
                    min=0.0,
                    max=1.0,
                    value=0.2,
                    step=0.05
                ),
                ui.input_slider(
                    "weight_brand",
                    "Brand Weight:",
                    min=0.0,
                    max=1.0,
                    value=0.1,
                    step=0.05
                ),
                ui.input_slider(
                    "weight_barcode",
                    "Barcode Weight:",
                    min=0.0,
                    max=1.0,
                    value=0.1,
                    step=0.05
                ),
                ui.output_text("weight_sum_warning")
            ),
            ui.output_ui("similarity_section"),
        ),
    ),
    ui.nav_panel(
        "Review & Validation",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_action_button("approve", "Approve Match"),
                ui.input_action_button("reject", "Reject / Create New Entry"),
            ),
            ui.output_table("review_table"),
        ),
    ),
    title="Food Product Similarity Dashboard",
)


# ================================
# SERVER
# ================================
def server(input, output, session):

    # ----------------------
    # Initialize DuckDB Connection
    # ----------------------
    con = duckdb.connect(database=':memory:')

    # ----------------------
    # Reactive Values
    # ----------------------
    similarity_results = reactive.Value({})
    selected_product_ids = reactive.Value([])
    created_handlers = set()

    # ----------------------
    # Load CSV into DuckDB
    # ----------------------
    csv_path = os.path.join(os.path.dirname(__file__), "view_food_clean.csv")

    try:
        if os.path.exists(csv_path):
            print(f"Loading CSV from: {csv_path}")
            df_temp = pd.read_csv(csv_path)

            if 'deleted' in df_temp.columns:
                df_temp = df_temp[df_temp["deleted"].isna()]

            print(f"Loaded {len(df_temp)} rows from CSV")
            con.execute("CREATE TABLE products AS SELECT * FROM df_temp")

            result = con.execute(
                "SELECT COUNT(*) as count FROM products").fetchone()
            print(f"Products table created with {result[0]} rows")
        else:
            print(f"CSV not found at {csv_path}, creating sample data")
            con.execute("""
                CREATE TABLE products AS 
                SELECT * FROM (VALUES
                    (1, 'Apple Juice', 'Beverage', 45, 0.2, 0.0, 1),
                    (2, 'Orange Juice', 'Beverage', 50, 0.3, 0.1, 0),
                    (3, 'Tomato Soup', 'Soup', 80, 2.0, 3.5, 0)
                ) AS t(id, name, categories, energy, protein, fat, active)
            """)
            print("Sample products table created")
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        import traceback
        traceback.print_exc()
        con.execute("""
            CREATE TABLE products (
                id INTEGER,
                name VARCHAR,
                categories VARCHAR,
                energy DOUBLE,
                protein DOUBLE,
                fat DOUBLE,
                active INTEGER
            )
        """)
        print("Created empty products table due to error")

    # ----------------------
    # Helper function to check API
    # ----------------------
    def check_api():
        """Check if similarity API is running"""
        try:
            response = requests.get(f"{SIMILARITY_API_URL}/", timeout=2)
            return response.status_code == 200
        except:
            return False

    # ----------------------
    # Filtered DataFrame
    # ----------------------
    def filtered_df():
        f = input.active_filter()

        try:
            if f == "1":
                query = "SELECT * FROM products WHERE active = 1"
            elif f == "0":
                query = "SELECT * FROM products WHERE active = 0"
            else:
                query = "SELECT * FROM products"

            return con.execute(query).df().reset_index(drop=True)
        except Exception as e:
            print(f"Error filtering data: {str(e)}")
            return pd.DataFrame()

    # ----------------------
    # Product Table Output
    # ----------------------
    @output
    @render.data_frame
    def product_table():
        return render.DataTable(filtered_df(), selection_mode="rows")

    # ----------------------
    # Track Selection
    # ----------------------
    @reactive.Effect
    def _track_selection():
        sel = product_table.cell_selection()
        if not sel or not sel["rows"]:
            selected_product_ids.set([])
            return
        ids = filtered_df().iloc[list(sel["rows"])]["id"].tolist()
        selected_product_ids.set(ids)

    # ----------------------
    # Weight Sum Warning
    # ----------------------
    @output
    @render.text
    def weight_sum_warning():
        total = (input.weight_text() + input.weight_nutrition() +
                 input.weight_brand() + input.weight_barcode())

        if abs(total - 1.0) > 0.01:
            return f"⚠️ Weights sum to {total:.2f}, should be 1.0"
        return f"✓ Weights sum to {total:.2f}"

    # ----------------------
    # Compute Similarity via API
    # ----------------------
    def compute_similarity(pid):
        try:
            # Check if API is running
            if not check_api():
                print("❌ Similarity API is not running!")
                store = similarity_results.get().copy()
                store[pid] = pd.DataFrame({
                    "Error": ["Similarity API is not running. Please start the API server."]
                })
                similarity_results.set(store)
                return

            # Prepare API request
            weights = {
                "text": input.weight_text(),
                "nutrition": input.weight_nutrition(),
                "brand": input.weight_brand(),
                "barcode": input.weight_barcode()
            }

            payload = {
                "product_id": pid,
                "top_n": 10,
                "weights": weights
            }

            # Call API
            response = requests.post(
                f"{SIMILARITY_API_URL}/similar",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Convert to DataFrame for display
                similar_prods = data['similar_products']
                res = pd.DataFrame([
                    {
                        'Rank': p['rank'],
                        'ID': p['id'],
                        'Name': p['name'],
                        'Brand': p['brand'],
                        'Score': f"{p['similarity_score']:.4f}",
                        'Energy': p['nutrition']['energy'],
                        'Protein': p['nutrition']['protein'],
                        'Fat': p['nutrition']['fat']
                    }
                    for p in similar_prods
                ])

                store = similarity_results.get().copy()
                store[pid] = res
                similarity_results.set(store)

                print(f"✅ Found {len(res)} similar products for ID {pid}")
                print(f"   Computation time: {data['computation_time_ms']} ms")
            else:
                print(f"❌ API error: {response.status_code}")
                store = similarity_results.get().copy()
                store[pid] = pd.DataFrame({
                    "Error": [f"API returned error: {response.json().get('error', 'Unknown error')}"]
                })
                similarity_results.set(store)

        except Exception as e:
            print(f"❌ Error computing similarity: {str(e)}")
            import traceback
            traceback.print_exc()

            store = similarity_results.get().copy()
            store[pid] = pd.DataFrame({
                "Error": [f"Error: {str(e)}"]
            })
            similarity_results.set(store)

    # ----------------------
    # Similarity Button Handlers
    # ----------------------
    @reactive.Effect
    def _watch_similarity_buttons():
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
        ids = selected_product_ids.get()

        if not ids:
            return ui.card("No products selected. Select rows from the Data & New Entries tab.")

        # Check API status
        api_status = check_api()
        if not api_status:
            return ui.card(
                ui.h4("⚠️ Similarity API Not Running"),
                ui.p("The similarity API server is not running or not accessible."),
                ui.p(f"Expected URL: {SIMILARITY_API_URL}"),
                ui.p("Please start the API server with:"),
                ui.tags.code("python api_similarity.py"),
                class_="alert alert-warning"
            )

        cards = []

        for pid in ids:
            try:
                row = con.execute(
                    "SELECT * FROM products WHERE id = ?", [pid]).df().iloc[0]
                table_id = f"similarity_table_{pid}"

                @output(id=table_id)
                @render.table
                def _render(pid=pid):
                    results = similarity_results.get()
                    if pid not in results:
                        return pd.DataFrame({
                            "Info": [f"Click 'Run Similarity' to find matches for product {pid}."]
                        })
                    return results[pid]

                cards.append(
                    ui.card(
                        ui.h4(f"{row['name']} (ID: {pid})"),
                        ui.tags.ul(
                            ui.tags.li(
                                f"Category: {row.get('categories', 'N/A')}"),
                            ui.tags.li(f"Energy: {row.get('energy', 'N/A')}"),
                            ui.tags.li(
                                f"Protein: {row.get('protein', 'N/A')} g"),
                            ui.tags.li(f"Fat: {row.get('fat', 'N/A')} g"),
                        ),
                        ui.input_action_button(
                            f"run_similarity_{pid}",
                            "🔍 Run Similarity",
                            class_="btn btn-primary"
                        ),
                        ui.hr(),
                        ui.h5("Similarity Results"),
                        ui.output_table(table_id),
                        class_="mb-4 p-3 border rounded shadow-sm",
                    )
                )
            except Exception as e:
                print(f"Error creating card for product {pid}: {str(e)}")
                continue

        return ui.div(*cards)

    # ----------------------
    # Cleanup
    # ----------------------
    @reactive.Effect
    def _cleanup():
        session.on_ended(lambda: con.close())


# ================================
# RUN APP
# ================================
app = App(app_ui, server)

if __name__ == "__main__":
    run_app(app, host="127.0.0.1", port=8000)
