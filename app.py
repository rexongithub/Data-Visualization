from shiny import App, ui, render, reactive, run_app
import pandas as pd
import duckdb
import os
from test import find_similar_products


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
                ui.h4("Similarity Options")
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
    # Create an in-memory database connection
    con = duckdb.connect(database=':memory:')

    # ----------------------
    # Reactive Values
    # ----------------------
    similarity_results = reactive.Value({})
    selected_product_ids = reactive.Value([])

    # keep track of which handlers were created
    created_handlers = set()

    # ----------------------
    # Load CSV into DuckDB
    # ----------------------
    csv_path = os.path.join(os.path.dirname(__file__), "view_food_clean.csv")
    if os.path.exists(csv_path):
        # Load CSV directly into DuckDB
        con.execute(f"""
            CREATE TABLE products AS 
            SELECT * FROM read_csv_auto('{csv_path}')
            WHERE deleted IS NULL
        """)
    else:
        # Create sample data table
        con.execute("""
            CREATE TABLE products AS 
            SELECT * FROM (VALUES
                (1, 'Apple Juice', 'Beverage', 45, 0.2, 0.0, 1),
                (2, 'Orange Juice', 'Beverage', 50, 0.3, 0.1, 0),
                (3, 'Tomato Soup', 'Soup', 80, 2.0, 3.5, 0)
            ) AS t(id, name, categories, energy, protein, fat, active)
        """)

    # ----------------------
    # Helper function to get all products as DataFrame
    # ----------------------
    def get_all_products():
        """Fetch all products from DuckDB as a pandas DataFrame"""
        return con.execute("SELECT * FROM products").df()

    # ----------------------
    # Filtered DataFrame
    # ----------------------
    def filtered_df():
        f = input.active_filter()

        if f == "1":
            query = "SELECT * FROM products WHERE active = 1"
        elif f == "0":
            query = "SELECT * FROM products WHERE active = 0"
        else:  # "all"
            query = "SELECT * FROM products"

        return con.execute(query).df().reset_index(drop=True)

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
    # Compute Similarity
    # ----------------------
    def compute_similarity(pid):
        # Get all products for similarity computation
        df = get_all_products()
        matches = find_similar_products(df, pid, top_n=10)

        # Query DuckDB for the matched products
        if matches:
            placeholders = ','.join('?' * len(matches))
            query = f"""
                SELECT id, name, categories, energy, protein, fat 
                FROM products 
                WHERE id IN ({placeholders})
            """
            res = con.execute(query, matches).df()
        else:
            res = pd.DataFrame(
                columns=["id", "name", "categories", "energy", "protein", "fat"])

        store = similarity_results.get().copy()
        store[pid] = res
        similarity_results.set(store)

    # ----------------------
    # Similarity Button Handlers
    # ----------------------
    @reactive.Effect
    def _watch_similarity_buttons():
        for pid in selected_product_ids.get():
            btn_id = f"run_similarity_{pid}"

            # Only create handler once
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
            return ui.card("No products selected.")

        cards = []

        for pid in ids:
            # Get product details from DuckDB
            row = con.execute(
                "SELECT * FROM products WHERE id = ?", [pid]).df().iloc[0]
            table_id = f"similarity_table_{pid}"

            @output(id=table_id)
            @render.table
            def _render(pid=pid):
                results = similarity_results.get()
                if pid not in results:
                    return pd.DataFrame({"Info": [f"Run similarity for product {pid}."]})
                return results[pid]

            cards.append(
                ui.card(
                    ui.h4(f"{row['name']} (ID: {pid})"),
                    ui.tags.ul(
                        ui.tags.li(
                            f"Category: {row.get('categories', 'N/A')}"),
                        ui.tags.li(f"Energy: {row.get('energy', 'N/A')}"),
                        ui.tags.li(f"Protein: {row.get('protein', 'N/A')} g"),
                        ui.tags.li(f"Fat: {row.get('fat', 'N/A')} g"),
                    ),
                    ui.input_action_button(
                        f"run_similarity_{pid}", "Run Similarity"),
                    ui.hr(),
                    ui.h5("Similarity Results"),
                    ui.output_table(table_id),
                    class_="mb-4 p-3 border rounded shadow-sm",
                )
            )

        return ui.div(*cards)

    # ----------------------
    # Cleanup on session end
    # ----------------------
    @reactive.Effect
    def _cleanup():
        # This will be called when the session ends
        session.on_ended(lambda: con.close())


# ================================
# RUN APP
# ================================
app = App(app_ui, server)

if __name__ == "__main__":
    run_app(app, host="127.0.0.1", port=8000)
