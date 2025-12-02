import pandas as pd

# Load CSV
df = pd.read_csv("view_food_clean.csv")

# 1. Filter out deleted rows
df = df[df["deleted"].isna()]

# -----------------------------
# A. Count active vs non-active
# -----------------------------
active_counts = df["active"].value_counts(dropna=False)

print("=== Active vs Non-Active Products ===")
print(active_counts)
print()

# -----------------------------------------
# B. Count products with required nutrients
# -----------------------------------------
nutrient_cols = [
    "energy",
    "carbohydrates",
    "fat",
    "protein",
    "saturated_fatty_acid",
    "sugar",
    "salt",
]

# products where all selected nutrient columns are non-null
has_nutrients = df.dropna(subset=nutrient_cols)

nutrient_active_counts = has_nutrients["active"].value_counts(dropna=False)

print("=== Active vs Non-Active WITH nutrient values ===")
print(nutrient_active_counts)
print()

# ------------------------------------------------------
# C. Barcode duplicates (barcodes separated by ';')
# ------------------------------------------------------

# Expand barcodes into rows
df_barcodes = (
    df.assign(barcode=df["barcode"].fillna("").astype(str))
      .assign(barcode=lambda x: x["barcode"].str.split(";"))
      .explode("barcode")
)

# Remove empty barcode entries
df_barcodes = df_barcodes[df_barcodes["barcode"].str.strip() != ""]

# Count barcode occurrences
barcode_counts = df_barcodes["barcode"].value_counts()

duplicates = barcode_counts[barcode_counts > 1]

print("=== Duplicate Barcodes (count > 1) ===")
print(duplicates)
print()

print(f"Total unique barcodes: {len(barcode_counts)}")
print(f"Barcodes used more than once: {len(duplicates)}")
