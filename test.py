import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def find_similar_products(
    df,
    non_active_id,
    top_n=10,
    w_text=0.7,
    w_nutrition=0.2,
    w_brand=0.1,
    w_barcode=0.1
):
    print("starting check")

    # Convert active to numeric
    df["active"] = pd.to_numeric(df["active"], errors="coerce")

    # Filter out deleted items
    df = df[df["deleted"].isna()]

    # Preprocessing function
    def clean_text(text):
        if pd.isna(text):
            return ""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # Active products
    active_df = df[df["active"] == 1].copy()
    active_df["text_combined"] = (
        active_df["name_search"].apply(clean_text) + " " +
        active_df["brands_search"].apply(clean_text)
    )

    # Load model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    active_embeddings = model.encode(active_df["text_combined"].tolist(), convert_to_numpy=True)

    # Nutrition columns
    nutrition_cols = ["energy","carbohydrates","fat","protein",
                      "saturated_fatty_acid","sugar","salt"]

    # ✅ Get the row safely
    rowset = df[(df["active"] == 0) & (df["id"] == non_active_id)]
    if rowset.empty:
        raise ValueError(f"No non-active product found with ID {non_active_id}")

    non_active_row = rowset.iloc[0]

    # Text similarity
    text = (
        clean_text(str(non_active_row.get("name_search", ""))) + " " +
        clean_text(str(non_active_row.get("brands_search", "")))
    )
    text_emb = model.encode([text], convert_to_numpy=True)
    text_sim = cosine_similarity(text_emb, active_embeddings).flatten()

    # Nutrition similarity
    nutrition_sim = np.zeros(len(active_df))
    nutrition_values = non_active_row[nutrition_cols].values.astype(float)

    if not np.all(np.isnan(nutrition_values)):
        valid_cols = ~np.isnan(nutrition_values)
        for i, col in enumerate(nutrition_cols):
            if valid_cols[i]:
                diff = active_df[col].fillna(0).values - nutrition_values[i]
                nutrition_sim += -np.abs(diff)
        nutrition_sim /= np.sum(valid_cols)

    # Brand match
    brand_sim = np.array([
        1.0 if clean_text(non_active_row.get("brands_search", "")) ==
                clean_text(str(b)) and b else 0.0
        for b in active_df["brands_search"]
    ])

    # Barcode match
    barcode_sim = np.array([
        1.0 if str(non_active_row.get("barcode","")) == str(bc) and bc else 0.0
        for bc in active_df["barcode"]
    ])

    # Combine
    combined_score = (
        w_text * text_sim +
        w_nutrition * nutrition_sim +
        w_brand * brand_sim +
        w_barcode * barcode_sim
    )

    top_idx = combined_score.argsort()[::-1][:top_n]

    result_ids = active_df.iloc[top_idx]["id"].tolist()
    print(result_ids)
    print("all done")
    return result_ids