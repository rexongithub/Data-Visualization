from shiny import App, ui, render, reactive, run_app
import pandas as pd
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
                    choices={"all": "All", "1": "Active Only", "0": "Inactive Only"},
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
    # Reactive Values
    # ----------------------
    product_data = reactive.Value(pd.DataFrame())
    similarity_results = reactive.Value({})
    selected_product_ids = reactive.Value([])

    # keep track of which handlers were created
    created_handlers = set()

    # ----------------------
    # Load CSV
    # ----------------------
    csv_path = os.path.join(os.path.dirname(__file__), "view_food_clean.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df = df[df["deleted"].isna()]
    else:
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Apple Juice", "Orange Juice", "Tomato Soup"],
            "categories": ["Beverage", "Beverage", "Soup"],
            "energy": [45, 50, 80],
            "protein": [0.2, 0.3, 2.0],
            "fat": [0.0, 0.1, 3.5],
            "active": [1, 0, 0],
        })

    product_data.set(df)

    # ----------------------
    # Filtered DataFrame
    # ----------------------
    def filtered_df():
        df = product_data.get().copy()
        f = input.active_filter()
        if f == "1":
            df = df[df["active"] == 1]
        elif f == "0":
            df = df[df["active"] == 0]
        return df.reset_index(drop=True)

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
        df = product_data.get()
        matches = find_similar_products(df, pid, top_n=10)
        res = df[df["id"].isin(matches)][[
            "id", "name", "categories", "energy", "protein", "fat"
        ]]

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
        df = product_data.get()
        ids = selected_product_ids.get()

        if not ids:
            return ui.card("No products selected.")

        cards = []

        for pid in ids:
            row = df[df["id"] == pid].iloc[0]
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
                        ui.tags.li(f"Category: {row.get('categories', 'N/A')}"),
                        ui.tags.li(f"Energy: {row.get('energy', 'N/A')}"),
                        ui.tags.li(f"Protein: {row.get('protein', 'N/A')} g"),
                        ui.tags.li(f"Fat: {row.get('fat', 'N/A')} g"),
                    ),
                    ui.input_action_button(f"run_similarity_{pid}", "Run Similarity"),
                    ui.hr(),
                    ui.h5("Similarity Results"),
                    ui.output_table(table_id),
                    class_="mb-4 p-3 border rounded shadow-sm",
                )
            )

        return ui.div(*cards)


# ================================
# RUN APP
# ================================
app = App(app_ui, server)

if __name__ == "__main__":
    run_app(app, host="127.0.0.1", port=8000)