# api_similarity.py
from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = Flask(__name__)

# ============================================================
# GLOBAL: Preload model and data once at startup
# ============================================================
print("🔄 Loading model and data at startup...")

# Load the sentence transformer model ONCE
MODEL = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Model loaded")

# Load and preprocess data ONCE
CSV_PATH = os.path.join(os.path.dirname(__file__), "view_food_clean.csv")
df = pd.read_csv(CSV_PATH, low_memory=False)

# Convert active to numeric
df["active"] = pd.to_numeric(df["active"], errors="coerce")

# Filter out deleted items
df = df[df["deleted"].isna()]

# Nutrition columns (used in similarity calculation)
NUTRITION_COLS = ["energy", "carbohydrates", "fat", "protein",
                  "saturated_fatty_acid", "sugar", "salt"]

print(f"✅ Data loaded: {len(df)} total products")

# ============================================================
# Text cleaning function
# ============================================================


def clean_text(text):
    """Preprocess text for similarity matching"""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================
# Precompute ALL product embeddings (both active and inactive)
# ============================================================
print("🔄 Precomputing embeddings for all products...")
ALL_DF = df.copy()
ALL_DF["text_combined"] = (
    ALL_DF["name_search"].apply(clean_text) + " " +
    ALL_DF["brands_search"].apply(clean_text)
)
ALL_EMBEDDINGS = MODEL.encode(
    ALL_DF["text_combined"].tolist(),
    convert_to_numpy=True,
    show_progress_bar=True
)
print(f"✅ Embeddings computed for {len(ALL_DF)} products")
print("=" * 60)
print("🚀 API ready to accept requests!")
print("=" * 60)

# ============================================================
# API ENDPOINTS
# ============================================================


@app.route("/", methods=["GET"])
def index():
    """Health check endpoint"""
    return jsonify({
        "service": "Food Product Similarity API",
        "status": "running",
        "total_products": len(df),
        "active_products": len(df[df["active"] == 1]),
        "inactive_products": len(df[df["active"] == 0]),
        "model": "all-MiniLM-L6-v2",
        "endpoints": {
            "/": "Health check (this page)",
            "/similar": "POST - Find similar products",
            "/product/<id>": "GET - Get product details",
            "/stats": "GET - Get dataset statistics"
        }
    })


@app.route("/similar", methods=["POST"])
def find_similar():
    """
    Find similar products to a given product.
    Now returns both active and inactive products (excluding the query product itself).

    Expects JSON like:
    {
      "product_id": 26585,
      "top_n": 20,
      "weights": {
        "text": 0.8,
        "nutrition": 0.0,
        "brand": 0.1,
        "barcode": 0.1
      }
    }

    Returns:
    {
      "query_product": {...},
      "similar_products": [...],
      "computation_time_ms": 123
    }
    """
    import time
    start_time = time.time()

    # Parse request
    data = request.get_json()
    if data is None:
        return jsonify({"error": "No JSON body provided"}), 400

    try:
        product_id = int(data["product_id"])
    except (KeyError, ValueError):
        return jsonify({"error": "Missing or invalid 'product_id'"}), 400

    # Optional parameters with defaults
    top_n = int(data.get("top_n", 20))
    weights = data.get("weights", {})
    w_text = float(weights.get("text", 0.8))
    w_nutrition = float(weights.get("nutrition", 0.0))
    w_brand = float(weights.get("brand", 0.1))
    w_barcode = float(weights.get("barcode", 0.1))

    # Validate weights sum to ~1.0
    total_weight = w_text + w_nutrition + w_brand + w_barcode
    if not (0.99 <= total_weight <= 1.01):
        return jsonify({
            "error": f"Weights must sum to 1.0, got {total_weight}"
        }), 400

    # Get the query product
    rowset = df[df["id"] == product_id]
    if rowset.empty:
        return jsonify({
            "error": f"No product found with ID {product_id}"
        }), 404

    query_row = rowset.iloc[0]

    # Create comparison dataframe (all products except the query product)
    COMPARISON_DF = ALL_DF[ALL_DF["id"] != product_id].copy()
    comparison_embeddings = ALL_EMBEDDINGS[ALL_DF["id"] != product_id]

    # ========================================
    # 1. Text Similarity
    # ========================================
    text = (
        clean_text(str(query_row.get("name_search", ""))) + " " +
        clean_text(str(query_row.get("brands_search", "")))
    )
    text_emb = MODEL.encode([text], convert_to_numpy=True)
    text_sim = cosine_similarity(text_emb, comparison_embeddings).flatten()

    # ========================================
    # 2. Nutrition Similarity
    # ========================================
    nutrition_sim = np.zeros(len(COMPARISON_DF))
    nutrition_values = query_row[NUTRITION_COLS].values.astype(float)

    if not np.all(np.isnan(nutrition_values)):
        valid_cols = ~np.isnan(nutrition_values)
        for i, col in enumerate(NUTRITION_COLS):
            if valid_cols[i]:
                diff = COMPARISON_DF[col].fillna(
                    0).values - nutrition_values[i]
                nutrition_sim += -np.abs(diff)
        nutrition_sim /= np.sum(valid_cols)
        # Normalize to 0-1 range (simple min-max)
        if nutrition_sim.max() != nutrition_sim.min():
            nutrition_sim = (nutrition_sim - nutrition_sim.min()) / \
                (nutrition_sim.max() - nutrition_sim.min())

    # ========================================
    # 3. Brand Match
    # ========================================
    brand_sim = np.array([
        1.0 if clean_text(query_row.get("brands_search", "")) ==
        clean_text(str(b)) and b else 0.0
        for b in COMPARISON_DF["brands_search"]
    ])

    # ========================================
    # 4. Barcode Match
    # ========================================
    barcode_sim = np.array([
        1.0 if str(query_row.get("barcode", "")
                   ) == str(bc) and bc else 0.0
        for bc in COMPARISON_DF["barcode"]
    ])

    # ========================================
    # 5. Combine Scores
    # ========================================
    combined_score = (
        w_text * text_sim +
        w_nutrition * nutrition_sim +
        w_brand * brand_sim +
        w_barcode * barcode_sim
    )

    # Get top N
    top_idx = combined_score.argsort()[::-1][:top_n]
    result_ids = COMPARISON_DF.iloc[top_idx]["id"].tolist()
    scores = combined_score[top_idx].tolist()

    # Build detailed results
    similar_products = []
    for idx, (prod_id, score) in enumerate(zip(result_ids, scores)):
        prod_row = COMPARISON_DF[COMPARISON_DF["id"] == prod_id].iloc[0]
        similar_products.append({
            "rank": idx + 1,
            "id": int(prod_id),
            "name": str(prod_row.get("name_search", "")),
            "brand": str(prod_row.get("brands_search", "")),
            "barcode": str(prod_row.get("barcode", "")),
            "active": int(prod_row["active"]) if pd.notna(prod_row["active"]) else 0,
            "similarity_score": float(score),
            "nutrition": {
                col: float(prod_row[col]) if pd.notna(prod_row[col]) else None
                for col in NUTRITION_COLS
            }
        })

    # Computation time
    computation_time = (time.time() - start_time) * 1000  # ms

    return jsonify({
        "query_product": {
            "id": int(product_id),
            "name": str(query_row.get("name_search", "")),
            "brand": str(query_row.get("brands_search", "")),
            "barcode": str(query_row.get("barcode", "")),
            "active": int(query_row["active"]) if pd.notna(query_row["active"]) else 0,
            "nutrition": {
                col: float(query_row[col]) if pd.notna(
                    query_row[col]) else None
                for col in NUTRITION_COLS
            }
        },
        "similar_products": similar_products,
        "parameters": {
            "top_n": top_n,
            "weights": {
                "text": w_text,
                "nutrition": w_nutrition,
                "brand": w_brand,
                "barcode": w_barcode
            }
        },
        "computation_time_ms": round(computation_time, 2)
    })


@app.route("/product/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Get details of a specific product"""
    product = df[df["id"] == product_id]

    if product.empty:
        return jsonify({"error": f"Product {product_id} not found"}), 404

    row = product.iloc[0]
    return jsonify({
        "id": int(product_id),
        "name": str(row.get("name_search", "")),
        "brand": str(row.get("brands_search", "")),
        "barcode": str(row.get("barcode", "")),
        "active": int(row["active"]) if pd.notna(row["active"]) else None,
        "categories": str(row.get("categories", "")),
        "nutrition": {
            col: float(row[col]) if pd.notna(row[col]) else None
            for col in NUTRITION_COLS
        }
    })


@app.route("/stats", methods=["GET"])
def get_stats():
    """Get dataset statistics"""
    return jsonify({
        "total_products": len(df),
        "active_products": int((df["active"] == 1).sum()),
        "inactive_products": int((df["active"] == 0).sum()),
        "products_with_barcode": int(df["barcode"].notna().sum()),
        "products_with_brand": int(df["brands_search"].notna().sum()),
        "nutrition_stats": {
            col: {
                "mean": float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                "median": float(df[col].median()) if pd.notna(df[col].median()) else None,
                "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
            }
            for col in NUTRITION_COLS
        }
    })

# ============================================================
# ERROR HANDLERS
# ============================================================


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ============================================================
# RUN
# ============================================================


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",  # Accessible from other machines
        port=5000,
        debug=True
    )
