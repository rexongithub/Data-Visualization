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
                ui.input_select(
                    "feature",
                    "Select Feature for Similarity:",
                    ["Composition", "Product Category", "Nutritional Values", "Name Similarity"]
                ),
                ui.input_slider("threshold", "Similarity Threshold", 0.5, 1.0, 0.8, step=0.01),
                ui.input_action_button("run_similarity", "Run Similarity Check")
            ),
            ui.output_table("similarity_results"),
            ui.output_plot("similarity_plot")
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
            "ProductID": [1, 2, 3],
            "Name": ["Apple Juice", "Orange Juice", "Tomato Soup"],
            "Category": ["Beverage", "Beverage", "Soup"],
            "Calories": [45, 50, 80],
            "Protein": [0.2, 0.3, 2.0],
            "Fat": [0.0, 0.1, 3.5],
        })

    product_data.set(df)

    @output
    @render.data_frame
    def product_table():
        df = product_data.get()
        if df.empty:
            return pd.DataFrame({"Info": ["No data loaded yet."]})

        choice = input.active_filter()
        if choice == "1":
            df = df[df["active"] == 1]
        elif choice == "0":
            df = df[df["active"] == 0]

        # return the pandas DataFrame directly
        return df



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
    def similarity_results():
        df = similarity_data.get()
        return df if not df.empty else pd.DataFrame({"Info": ["Run similarity check to see results."]})

    # --- Similarity Plot ---
    @output
    @render.plot
    def similarity_plot():
        df = similarity_data.get()
        if df.empty:
            return
        fig = px.bar(df, x="Name", y="Similarity_Score", color="Similar_To", title="Similarity Scores by Product")
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