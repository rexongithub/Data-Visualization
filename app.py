from shiny import App, ui, render, reactive, run_app
import pandas as pd
import plotly.express as px
import os
from test import find_similar_products

# --- UI ---
app_ui = ui.page_navbar(
    ui.nav_panel(
        "Data & New Entries",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_radio_buttons(
                    "active_filter",
                    "Show Products:",
                    choices={
                        "all": "All",
                        "1": "Active Only",
                        "0": "Inactive Only",
                    },
                    selected="0",
                )
            ),
            ui.output_data_frame("product_table")
        )
    ),
    ui.nav_panel(
        "Similarity Suggestions",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("Similarity Options"),
                ui.help_text("Select products on the first tab to see them here.")
            ),
            ui.output_ui("selected_product_sections"),
            ui.hr(),
            ui.h4("Similarity Results"),
            ui.output_table("similarity_results")

        )
    ),
    ui.nav_panel(
        "Review & Validation",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_action_button("approve", "Approve Match"),
                ui.input_action_button("reject", "Reject / Create New Entry")
            ),
            ui.output_table("review_table")
        )
    ),
    title="Food Product Similarity Dashboard",
)

# --- SERVER ---
def server(input, output, session):
    product_data = reactive.Value(pd.DataFrame())
    similarity_data = reactive.Value(pd.DataFrame())

    # --- Load database immediately on startup ---
    csv_path = os.path.join(os.path.dirname(__file__), "view_food_clean.csv")

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df = df[df["deleted"].isna()]
    else:
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Apple Juice", "Orange Juice", "Tomato Soup"],
            "Category": ["Beverage", "Beverage", "Soup"],
            "Calories": [45, 50, 80],
            "protein": [0.2, 0.3, 2.0],
            "Fat": [0.0, 0.1, 3.5],
            "active": [1, 0, 0],  # Added 'active' column for demo
        })

    product_data.set(df)

    def filtered_df():
        d = product_data.get().copy()
        choice = input.active_filter()
        if choice == "1" and "active" in d.columns:
            d = d[d["active"] == 1]
        elif choice == "0" and "active" in d.columns:
            d = d[d["active"] == 0]
        return d.reset_index(drop=True)

    selected_product_ids = reactive.Value([])

    # --- Product Table ---
    @output
    @render.data_frame
    def product_table():
        return render.DataTable(
            filtered_df(),
            selection_mode="rows"
        )

    # --- Track selection ---
    @reactive.Effect
    def track_selection():
        sel = product_table.cell_selection()
        if sel is None:
            selected_product_ids.set([])
        else:
            rows = sel["rows"]
            if rows:
                d = filtered_df()
                ids = d.iloc[list(rows)]["id"].tolist()
            else:
                ids = []
            selected_product_ids.set(ids)

    # --- Dynamically generate product sections ---
    @output
    @render.ui
    def selected_product_sections():
        df = product_data.get()
        ids = selected_product_ids.get()
        if df.empty or not ids:
            return ui.card(ui.p("No products selected. Go to 'Data & New Entries' to select some."))

        sections = []
        for pid in ids:
            product = df[df["id"] == pid].iloc[0]

            # Check active status (defaults to 0/inactive if column missing)
            is_active = int(product.get("active", 0)) == 1

            # Conditional styling & content
            box_style = (
                "p-3 mb-4 border rounded shadow-sm text-white bg-danger"
                if is_active
                else "p-3 mb-4 border rounded shadow-sm bg-light"
            )

            contents = [
                ui.h4(f"Product: {product['name']}"),
                ui.tags.ul(
                    ui.tags.li(f"ID: {pid}"),
                    ui.tags.li(f"Category: {product.get('categories', 'N/A')}"),
                    ui.tags.li(f"Energy: {product.get('energy', 'N/A')}"),
                    ui.tags.li(f"Protein: {product.get('protein', 'N/A')} g"),
                    ui.tags.li(f"Fat: {product.get('fat', 'N/A')} g"),
                ),
            ]

            if not is_active:
                contents.append(ui.input_action_button(f"run_similarity_{pid}", "Run Similarity Check"))
            else:
                contents.append(ui.p("Active products cannot be re-analyzed.", class_="fw-bold"))

            sections.append(ui.card(*contents, class_=box_style))

        return ui.div(*sections)

    # --- Review Table ---
    @output
    @render.table
    def review_table():
        df = similarity_data.get()
        if df.empty:
            return pd.DataFrame({"Info": ["No similarity results yet."]})
        return df[["name", "Similar_To", "Similarity_Score"]]
    
    # --- Handle dynamic similarity buttons ---
    @reactive.Effect
    def listen_similarity_buttons():
        ids = selected_product_ids.get()  # which products are shown
        for pid in ids:
            btn_id = f"run_similarity_{pid}"

            # check if this input exists
            if btn_id in input:

                # create an isolated effect for THIS button
                @reactive.Effect
                def _button_handler(pid=pid, btn_id=btn_id):
                    if input[btn_id]():  # button clicked
                        run_similarity(pid)

    def run_similarity(pid):
        df = product_data.get()
        
        # result = list of active product IDs
        result_ids = find_similar_products(df, pid, top_n=10)

        # extract those rows from the main dataframe
        matched_rows = df[df["id"].isin(result_ids)][
            ["id", "name", "brands", "barcode", "categories", "energy", "protein", "fat"]
        ]

        # store results
        similarity_data.set(matched_rows)

    @output
    @render.table
    def similarity_results():
        df = similarity_data.get()
        if df.empty:
            return pd.DataFrame({"Info": ["Run a similarity check to see matches here."]})
        return df


# --- RUN APP ---
app = App(app_ui, server)

if __name__ == "__main__":
    run_app(app, host="127.0.0.1", port=8000)