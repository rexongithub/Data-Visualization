# app.py
from shiny import App, ui, render, reactive, run_app
import pandas as pd
import plotly.express as px
import os

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
                    selected="all",
                )
            ),
            ui.output_data_frame("product_table")

        )
    ),
    ui.nav_panel(
        "Similarity Suggestions",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_action_button("run_similarity", "Run Similarity Check")
            ),
            ui.h4("Selected Products for Similarity Check"),
            ui.output_table("selected_products_table"),
            ui.output_plot("similarity_plot"),
            ui.output_text_verbatim("selected_ids_text")
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
    else:
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "Name": ["Apple Juice", "Orange Juice", "Tomato Soup"],
            "Category": ["Beverage", "Beverage", "Soup"],
            "Calories": [45, 50, 80],
            "Protein": [0.2, 0.3, 2.0],
            "Fat": [0.0, 0.1, 3.5],
        })

    product_data.set(df)

    def filtered_df():
        d = product_data.get().copy()
        choice = input.active_filter()
        if choice == "1" and "active" in d.columns:
            d = d[d["active"] == 1]
        elif choice == "0" and "active" in d.columns:
            d = d[d["active"] == 0]
        return d.reset_index(drop=True)  # reindex so .iloc works cleanly

    selected_product_ids = reactive.Value([])

    # Render the table with selection enabled
    @output
    @render.data_frame
    def product_table():
        # Use DataTable with multi-row selection
        return render.DataTable(
            filtered_df(),
            selection_mode="rows"  # allow multiple row selection
        )
    

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



    # Output text
    @output
    @render.text
    def selected_ids_text():
        return str(selected_product_ids.get())


    # --- Similarity Logic (mock) ---
    @reactive.effect
    @reactive.event(input.run_similarity)
    def compute_similarity():
        df = product_data.get()
        if df.empty:
            return
        sim_df = df.copy()
        sim_df["Similar_To"] = sim_df["Name"].shift(-1).fillna("None")
        sim_df["Similarity_Score"] = [0.92, 0.87, 0.55][:len(sim_df)]
        similarity_data.set(sim_df)

    # --- Similarity Table ---
    @output
    @render.table
    def selected_products_table():
        df = product_data.get()
        ids = selected_product_ids.get()
        if df.empty or not ids:
            return pd.DataFrame({"Info": ["No products selected."]})
        return df[df["id"].isin(ids)]


# --- Similarity Plot ---
    @output
    @render.plot
    def similarity_plot():
        df = similarity_data.get()
        if df.empty:
            return
        fig = px.bar(
            df,
            x="Name",
            y="Similarity_Score",
            color="Similar_To",
            title="Similarity Scores by Product"
        )
        return fig


    # --- Review Table ---
    @output
    @render.table
    def review_table():
        df = similarity_data.get()
        if df.empty:
            return pd.DataFrame({"Info": ["No similarity results yet."]})
        return df[["Name", "Similar_To", "Similarity_Score"]]

# --- RUN APP ---
app = App(app_ui, server)

if __name__ == "__main__":
    run_app(app, host="127.0.0.1", port=8000)