import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load CSV
df = pd.read_csv("view_food_clean.csv")

# Convert active to numeric
df["active"] = pd.to_numeric(df["active"], errors="coerce")

# Filter out deleted items
df = df[df["deleted"].isna()]

# Preprocessing function for search columns
def clean_text(text):
    if pd.isna(text):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)  # remove weird chars
    text = re.sub(r"\s+", " ", text).strip()
    return text

# Apply preprocessing to active products
active_df = df[df["active"] == 1].copy()
active_df["text_combined"] = (
    active_df["name_search"].apply(clean_text) + " " +
    active_df["brands_search"].apply(clean_text)
)

# Model for embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")
active_embeddings = model.encode(active_df["text_combined"].tolist(), convert_to_numpy=True)

# Columns for nutrition (optional)
nutrition_cols = ["energy","carbohydrates","fat","protein","saturated_fatty_acid","sugar","salt"]

def find_similar_products(non_active_id, top_n=10, w_text=0.7, w_nutrition=0.2, w_brand=0.1, w_barcode=0.1):
    non_active_row = df[(df["active"] == 0) & (df["id"] == non_active_id)].iloc[0]

    # Text embedding for non-active product
    text = clean_text(str(non_active_row["name_search"])) + " " + clean_text(str(non_active_row.get("brands_search", "")))
    text_emb = model.encode([text], convert_to_numpy=True)
    text_sim = cosine_similarity(text_emb, active_embeddings).flatten()

    # Nutrition similarity (if available)
    nutrition_sim = np.zeros(len(active_df))
    nutrition_values = non_active_row[nutrition_cols].values.astype(float)
    if not np.all(pd.isna(nutrition_values)):
        for i, col in enumerate(nutrition_cols):
            if pd.notna(nutrition_values[i]):
                col_active = active_df[col].fillna(0).values
                nutrition_sim += -np.abs(col_active - nutrition_values[i])
        nutrition_sim = nutrition_sim / np.count_nonzero(~pd.isna(nutrition_values))

    # Brand match boost
    brand_sim = np.array([
        1.0 if clean_text(str(non_active_row.get("brands_search",""))) == clean_text(str(b)) and b else 0.0
        for b in active_df["brands_search"]
    ])

    # Barcode exact match boost
    barcode_sim = np.array([
        1.0 if str(non_active_row.get("barcode","")) == str(bc) and bc else 0.0
        for bc in active_df["barcode"]
    ])

    # Combine similarities
    combined_score = (
        w_text * text_sim +
        w_nutrition * nutrition_sim +
        w_brand * brand_sim +
        w_barcode * barcode_sim
    )

    # Return top N active product IDs
    top_idx = combined_score.argsort()[::-1][:top_n]
    return active_df.iloc[top_idx]["id"].tolist()

# Example usage
non_active_id = 26585  # replace with your non-active product id
top_active_ids = find_similar_products(non_active_id, top_n=10)
print("Top 10 similar active product IDs:", top_active_ids)