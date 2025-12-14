# Food Product Similarity Dashboard

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Application Workflow](#application-workflow)
4. [Installation & Setup](#installation--setup)
5. [Running the Application](#running-the-application)
6. [Data Processing](#data-processing)
7. [Architecture](#architecture)
8. [File Structure](#file-structure)

---

## Overview

### What does this application do?

The **Food Product Similarity Dashboard** is a web-based tool designed to help food database administrators manage and consolidate duplicate or similar food products. It uses machine learning-based text similarity (sentence embeddings) combined with nutritional data matching to identify products that may be duplicates or variations of the same item.

### Why was it built?

Food product databases often contain:

- **Duplicate entries**: The same product entered multiple times with slightly different names
- **Inactive products**: Products that need to be reviewed and either activated or linked to existing active products
- **Barcode variations**: The same product with different barcodes from different retailers

This application streamlines the process of:

1. Identifying similar products using AI-powered similarity matching
2. Comparing products side-by-side to verify they are indeed duplicates
3. Linking duplicate products together (merging barcodes)
4. Activating reviewed products to make them available in the main database

---

## Features

### What does the app show?

| Tab                        | Purpose                                     | Why It's Needed                                                                 |
| -------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| **Data & New Entries**     | Browse active and inactive products         | Provides an overview of the database and allows selection of products to review |
| **Similarity Suggestions** | Shows AI-generated list of similar products | Helps identify potential duplicates without manual searching                    |
| **Product Editor**         | Edit product details and activate products  | Allows corrections before making a product active in the database               |

### Key Functionality

- **Text-based similarity**: Uses sentence transformers (all-MiniLM-L6-v2) to find products with similar names and brands
- **Nutritional similarity**: Compares energy, protein, fat, carbohydrates, sugar, and salt values
- **Brand matching**: Boosts similarity scores for products from the same brand
- **Barcode matching**: Identifies exact barcode matches
- **Product linking**: Merges barcodes from duplicate products and marks duplicates as deleted
- **Side-by-side comparison**: Visual comparison highlighting differences between products

---

## Application Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TYPICAL USER WORKFLOW                         │
└─────────────────────────────────────────────────────────────────────┘

1. DATA & NEW ENTRIES
   └── User browses inactive products
   └── Clicks on a product row to investigate
                    │
                    ▼
2. SIMILARITY SUGGESTIONS
   └── System shows 20 most similar products (active & inactive)
   └── User clicks "Compare" to see side-by-side details
   └── User marks similar products for review
                    │
                    ▼
3. REVIEW & VALIDATION (via sidebar)
   └── User reviews all marked products
   └── Clicks "Link Products" to merge them
                    │
                    ▼
4. PRODUCT EDITOR
   └── User edits/corrects product information
   └── Clicks "Save & Activate" to finalize
   └── Linked products are marked as deleted
   └── Barcodes are merged to the active product
```

---

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Required Packages

Install all dependencies using pip:

```bash
pip install shiny pandas duckdb flask requests scikit-learn sentence-transformers numpy
```

#### Package Details

| Package                 | Version | Purpose                                   |
| ----------------------- | ------- | ----------------------------------------- |
| `shiny`                 | ≥0.6.0  | Web application framework (Python Shiny)  |
| `pandas`                | ≥1.5.0  | Data manipulation and analysis            |
| `duckdb`                | ≥0.9.0  | In-memory SQL database for fast queries   |
| `flask`                 | ≥2.0.0  | REST API framework for similarity service |
| `requests`              | ≥2.28.0 | HTTP client for API communication         |
| `scikit-learn`          | ≥1.0.0  | Cosine similarity calculations            |
| `sentence-transformers` | ≥2.2.0  | Text embeddings for similarity matching   |
| `numpy`                 | ≥1.21.0 | Numerical computations                    |

### Required Files

```
project/
├── app.py                  # Main application entry point
├── server.py               # Shiny server logic and event handlers
├── ui_components.py        # UI component definitions
├── database.py             # Database operations (DuckDB)
├── api_client.py           # Client for similarity API
├── similar_food_api.py     # Flask API for similarity computation
├── config.py               # Configuration settings
└── view_food_clean.csv     # Food product dataset (required)
```

### Configuration

Edit `config.py` to customize settings:

```python
# API Configuration
SIMILARITY_API_URL = "http://localhost:5000"

# Database Configuration
DATABASE_PATH = ":memory:"          # In-memory database (resets on restart)
CSV_FILENAME = "view_food_clean.csv"

# App Configuration
APP_HOST = "127.0.0.1"
APP_PORT = 8000

# Similarity weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "text": 0.9,        # Name/brand text similarity
    "nutrition": 0.03,  # Nutritional values similarity
    "brand": 0.07,      # Exact brand match bonus
    "barcode": 0.0      # Exact barcode match bonus
}

# Number of similar products to return
TOP_N_RESULTS = 20
```

---

## Running the Application

### Step 1: Start the Similarity API

The similarity API must be running before starting the main application. This service handles the computationally intensive embedding calculations.

```bash
python similar_food_api.py
```

Expected output:

```
🔄 Loading model and data at startup...
✅ Model loaded
✅ Data loaded: XXXXX total products
🔄 Precomputing embeddings for all products...
✅ Embeddings computed for XXXXX products
============================================================
🚀 API ready to accept requests!
============================================================
 * Running on http://0.0.0.0:5000
```

**Note:** The first startup takes 1-2 minutes as it loads the sentence transformer model and precomputes embeddings for all products.

### Step 2: Start the Main Application

In a new terminal window:

```bash
python app.py
```

Expected output:

```
============================================================
Food Product Similarity Dashboard
============================================================
Starting server at http://127.0.0.1:8000
Make sure the similarity API is running on port 5000
============================================================
```

### Step 3: Access the Application

Open your web browser and navigate to:

```
http://127.0.0.1:8000
```

---

## Data Processing

### Data Source

The application expects a CSV file named `view_food_clean.csv` containing food product data.

### Required CSV Columns

| Column                 | Type            | Description                                              |
| ---------------------- | --------------- | -------------------------------------------------------- |
| `id`                   | Integer         | Unique product identifier                                |
| `name_search`          | String          | Product name (used for similarity matching)              |
| `brands_search`        | String          | Brand name(s)                                            |
| `barcode`              | String          | Product barcode(s), semicolon-separated if multiple      |
| `categories`           | String          | Product categories                                       |
| `active`               | Integer         | 1 = active, 0 = inactive                                 |
| `deleted`              | String/DateTime | Timestamp when product was deleted (NULL if not deleted) |
| `energy`               | Float           | Energy content (kcal/kJ per 100g)                        |
| `protein`              | Float           | Protein content (g per 100g)                             |
| `fat`                  | Float           | Fat content (g per 100g)                                 |
| `saturated_fatty_acid` | Float           | Saturated fat (g per 100g)                               |
| `carbohydrates`        | Float           | Carbohydrate content (g per 100g)                        |
| `sugar`                | Float           | Sugar content (g per 100g)                               |
| `salt`                 | Float           | Salt content (g per 100g)                                |

### Data Loading Process

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LOADING PIPELINE                          │
└─────────────────────────────────────────────────────────────────────┘

1. CSV FILE (view_food_clean.csv)
   │
   ▼
2. PANDAS DATAFRAME
   └── Read CSV with pandas
   └── Filter out already deleted products (deleted IS NOT NULL)
   └── Drop 'deleted' and 'linked_items' columns (recreated fresh)
   │
   ▼
3. DUCKDB IN-MEMORY DATABASE
   └── Create 'products' table from DataFrame
   └── Add 'deleted' column (VARCHAR) for tracking deletions
   └── Add 'linked_items' column (VARCHAR) for tracking links
   │
   ▼
4. SIMILARITY API (separate process)
   └── Load same CSV file
   └── Filter out deleted products
   └── Clean text (lowercase, remove special characters)
   └── Combine name + brand into single text field
   └── Generate sentence embeddings for ALL products
   └── Store embeddings in memory for fast similarity queries
```

### Data Transformations

#### Text Cleaning (for similarity matching)

```python
def clean_text(text):
    text = str(text).lower()                    # Lowercase
    text = re.sub(r"[^a-z0-9\s]", "", text)    # Remove special chars
    text = re.sub(r"\s+", " ", text).strip()   # Normalize whitespace
    return text
```

#### Similarity Score Calculation

```
Final Score = (w_text × text_similarity) +
              (w_nutrition × nutrition_similarity) +
              (w_brand × brand_match) +
              (w_barcode × barcode_match)

Where:
- text_similarity: Cosine similarity of sentence embeddings (0-1)
- nutrition_similarity: Normalized inverse of nutritional differences (0-1)
- brand_match: 1 if exact brand match, 0 otherwise
- barcode_match: 1 if exact barcode match, 0 otherwise
```

#### Product Linking Process

When products are linked:

1. All barcodes from linked products are merged (semicolon-separated)
2. The `linked_items` column is set to the ID of the master product
3. The `deleted` column is set to the current timestamp
4. Linked products are filtered out from all future queries

### Database Queries

The application uses DuckDB with the following key queries:

**Filtering Active/Inactive Products:**

```sql
SELECT * FROM products
WHERE (deleted IS NULL OR deleted = '')
  AND (linked_items IS NULL OR linked_items = '')
  AND active = 0  -- or active = 1 for active products
```

**Updating Product Status:**

```sql
UPDATE products
SET active = 1, name_search = ?, brands_search = ?, ...
WHERE id = ?
```

**Marking Products as Deleted:**

```sql
UPDATE products
SET deleted = '2024-01-01 12:00:00', linked_items = '12345'
WHERE id = ?
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SYSTEM ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     HTTP/JSON      ┌─────────────────────────────┐
│                 │ ◄─────────────────► │                             │
│  Shiny App      │    Port 5000       │  Flask Similarity API       │
│  (Port 8000)    │                    │                             │
│                 │                    │  - Sentence Transformer     │
│  - UI Rendering │                    │  - Precomputed Embeddings   │
│  - User Events  │                    │  - Cosine Similarity        │
│  - Navigation   │                    │                             │
└────────┬────────┘                    └──────────────┬──────────────┘
         │                                            │
         │                                            │
         ▼                                            ▼
┌─────────────────┐                    ┌─────────────────────────────┐
│                 │                    │                             │
│  DuckDB         │                    │  view_food_clean.csv        │
│  (In-Memory)    │ ◄────────────────► │                             │
│                 │    Loaded at       │  (Source Data)              │
│  - Products     │    Startup         │                             │
│  - CRUD Ops     │                    │                             │
└─────────────────┘                    └─────────────────────────────┘
```

---

## File Structure

```
project/
│
├── app.py                  # Entry point - creates and runs Shiny app
│
├── server.py               # Server logic
│   ├── Reactive values (state management)
│   ├── Navigation handlers
│   ├── Table renderers
│   ├── Selection tracking
│   ├── Similarity computation triggers
│   ├── Product marking/unmarking
│   ├── Link products handler
│   └── Save/activate product handler
│
├── ui_components.py        # UI definitions
│   ├── Main app layout (sidebar + content)
│   ├── Data panel (active/inactive tables)
│   ├── Similarity panel (results list)
│   ├── Editor panel (form fields)
│   ├── Comparison panel (side-by-side view)
│   └── CSS styles
│
├── database.py             # Database operations
│   ├── DatabaseManager class
│   ├── Initialize from CSV
│   ├── Filtered queries
│   ├── Product updates
│   ├── Link products (merge barcodes)
│   └── Activate products
│
├── api_client.py           # API client
│   ├── SimilarityAPIClient class
│   ├── Health check
│   └── Get similar products
│
├── similar_food_api.py     # Similarity API (Flask)
│   ├── Load model & data at startup
│   ├── Precompute embeddings
│   ├── /similar endpoint
│   ├── /product/<id> endpoint
│   └── /stats endpoint
│
├── config.py               # Configuration
│   ├── API URLs and ports
│   ├── Database settings
│   ├── Default weights
│   └── Field configurations
│
└── view_food_clean.csv     # Data file (not included)
```

## License

This project is provided as-is for educational and demonstration purposes.
