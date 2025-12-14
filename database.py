"""
Database operations for the Food Product Similarity Dashboard
"""
import duckdb
import pandas as pd
import os
from datetime import datetime
from config import DATABASE_PATH, CSV_FILENAME, COMPARISON_FIELDS


class DatabaseManager:
    """Manages DuckDB connection and operations"""

    def __init__(self):
        self.con = duckdb.connect(database=DATABASE_PATH)
        self._initialize_database()

    def _initialize_database(self):
        """Load CSV data into DuckDB or create sample data"""
        csv_path = os.path.join(os.path.dirname(__file__), CSV_FILENAME)

        try:
            if os.path.exists(csv_path):
                print(f"Loading CSV from: {csv_path}")
                df_temp = pd.read_csv(csv_path, low_memory=False)

                # Filter out deleted products (keep only where deleted is NaN/empty)
                if 'deleted' in df_temp.columns:
                    df_temp = df_temp[df_temp["deleted"].isna()]

                # Drop the deleted column - we'll recreate it with correct type
                if 'deleted' in df_temp.columns:
                    df_temp = df_temp.drop(columns=['deleted'])

                # Drop linked_items if it exists - we'll create it fresh
                if 'linked_items' in df_temp.columns:
                    df_temp = df_temp.drop(columns=['linked_items'])

                print(f"Loaded {len(df_temp)} rows from CSV")
                self.con.execute(
                    "CREATE TABLE products AS SELECT * FROM df_temp")

                # Add deleted column as VARCHAR
                self.con.execute(
                    "ALTER TABLE products ADD COLUMN deleted VARCHAR")
                print("Added 'deleted' column as VARCHAR")

                # Add linked_items column as VARCHAR
                self.con.execute(
                    "ALTER TABLE products ADD COLUMN linked_items VARCHAR")
                print("Added 'linked_items' column as VARCHAR")

                # Verify column types
                schema = self.con.execute("DESCRIBE products").fetchall()
                for col in schema:
                    if col[0] in ['deleted', 'linked_items']:
                        print(f"  Column '{col[0]}' type: {col[1]}")

                result = self.con.execute(
                    "SELECT COUNT(*) as count FROM products").fetchone()
                print(f"Products table created with {result[0]} rows")
            else:
                print(f"CSV not found at {csv_path}, creating sample data")
                self._create_sample_data()
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            import traceback
            traceback.print_exc()
            self._create_empty_table()

    def _create_sample_data(self):
        """Create sample products table"""
        self.con.execute("""
            CREATE TABLE products AS 
            SELECT * FROM (VALUES
                (1, 'Apple Juice', 'FruitCo', 'Beverage', '123456', 45, 0.2, 0.0, 0.0, 10.5, 9.0, 0.01, 1, NULL, NULL),
                (2, 'Orange Juice', 'FruitCo', 'Beverage', '123457', 50, 0.3, 0.1, 0.0, 11.0, 10.0, 0.02, 0, NULL, NULL),
                (3, 'Tomato Soup', 'SoupBrand', 'Soup', '234567', 80, 2.0, 3.5, 0.5, 8.0, 5.0, 0.8, 0, NULL, NULL)
            ) AS t(id, name_search, brands_search, categories, barcode, energy, protein, fat, saturated_fatty_acid, carbohydrates, sugar, salt, active, deleted, linked_items)
        """)
        print("Sample products table created")

    def _create_empty_table(self):
        """Create empty products table"""
        self.con.execute("""
            CREATE TABLE products (
                id INTEGER,
                name_search VARCHAR,
                brands_search VARCHAR,
                categories VARCHAR,
                barcode VARCHAR,
                energy DOUBLE,
                protein DOUBLE,
                fat DOUBLE,
                saturated_fatty_acid DOUBLE,
                carbohydrates DOUBLE,
                sugar DOUBLE,
                salt DOUBLE,
                active INTEGER,
                deleted VARCHAR,
                linked_items VARCHAR
            )
        """)
        print("Created empty products table due to error")

    def get_filtered_products(self, active_filter, search_term="", columns=None):
        """
        Get products filtered by active status and search term

        Args:
            active_filter: "all", "1" (active), or "0" (inactive)
            search_term: Optional search term for name or brand
            columns: Optional list of columns to select

        Returns:
            pandas DataFrame with filtered products
        """
        try:
            # Build column selection
            if columns:
                col_str = ", ".join(columns)
            else:
                col_str = "*"

            # Build WHERE clause - exclude deleted products and products linked to others
            # Use LENGTH check to be more robust against different NULL/empty representations
            conditions = [
                "(deleted IS NULL OR COALESCE(CAST(deleted AS VARCHAR), '') = '')",
                "(linked_items IS NULL OR COALESCE(CAST(linked_items AS VARCHAR), '') = '')"
            ]

            if active_filter == "1":
                conditions.append("active = 1")
            elif active_filter == "0":
                conditions.append("active = 0")

            if search_term:
                conditions.append(
                    f"(LOWER(name_search) LIKE '%{search_term.lower()}%' OR "
                    f"LOWER(brands_search) LIKE '%{search_term.lower()}%')"
                )

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT {col_str} FROM products WHERE {where_clause}"

            result = self.con.execute(query).df().reset_index(drop=True)

            # Debug: Log count of filtered results
            print(
                f"DEBUG get_filtered_products: active_filter={active_filter}, returned {len(result)} rows")

            return result
        except Exception as e:
            print(f"Error filtering data: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def get_product_by_id(self, product_id):
        """
        Get a single product by ID

        Args:
            product_id: Product ID to retrieve

        Returns:
            pandas Series with product data or None
        """
        try:
            # Convert numpy int64 to Python int if necessary
            if hasattr(product_id, 'item'):
                product_id = product_id.item()
            else:
                product_id = int(product_id)

            result = self.con.execute(
                "SELECT * FROM products WHERE id = ?",
                [product_id]
            ).df()

            if len(result) > 0:
                return result.iloc[0]
            return None
        except Exception as e:
            print(f"Error getting product {product_id}: {str(e)}")
            return None

    def get_products_by_ids(self, product_ids):
        """
        Get multiple products by their IDs

        Args:
            product_ids: List of product IDs to retrieve

        Returns:
            pandas DataFrame with product data
        """
        try:
            if not product_ids:
                return pd.DataFrame()

            # Convert to Python ints
            ids = [int(pid) if hasattr(pid, 'item') else int(pid)
                   for pid in product_ids]
            placeholders = ", ".join(["?" for _ in ids])

            result = self.con.execute(
                f"SELECT * FROM products WHERE id IN ({placeholders})",
                ids
            ).df()

            return result
        except Exception as e:
            print(f"Error getting products: {str(e)}")
            return pd.DataFrame()

    def update_product(self, product_id, updates):
        """
        Update a product's fields

        Args:
            product_id: Product ID to update
            updates: Dictionary of field names and new values

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not updates:
                return True

            # Convert product_id to Python int
            if hasattr(product_id, 'item'):
                product_id = product_id.item()
            else:
                product_id = int(product_id)

            # Build SET clause
            set_parts = []
            values = []
            for field, value in updates.items():
                set_parts.append(f"{field} = ?")
                values.append(value)

            set_clause = ", ".join(set_parts)
            values.append(product_id)

            query = f"UPDATE products SET {set_clause} WHERE id = ?"
            self.con.execute(query, values)

            print(f"Updated product {product_id}: {updates}")
            return True
        except Exception as e:
            print(f"Error updating product {product_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def link_products(self, active_product_id, products_to_link):
        """
        Link products to an active product:
        - Merge barcodes to active product
        - Set linked_items on linked products
        - Set deleted timestamp on linked products

        Args:
            active_product_id: ID of the active/master product
            products_to_link: List of product IDs to link (including original if not active)

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if hasattr(active_product_id, 'item'):
                active_product_id = active_product_id.item()
            else:
                active_product_id = int(active_product_id)

            # Get active product
            active_product = self.get_product_by_id(active_product_id)
            if active_product is None:
                return False, f"Active product {active_product_id} not found"

            # Collect all barcodes
            all_barcodes = set()

            # Add active product's barcodes
            if pd.notna(active_product.get('barcode')) and active_product.get('barcode'):
                for bc in str(active_product['barcode']).split(';'):
                    bc = bc.strip()
                    if bc:
                        all_barcodes.add(bc)

            # Get products to link and collect their barcodes
            products_df = self.get_products_by_ids(products_to_link)

            for _, row in products_df.iterrows():
                if pd.notna(row.get('barcode')) and row.get('barcode'):
                    for bc in str(row['barcode']).split(';'):
                        bc = bc.strip()
                        if bc:
                            all_barcodes.add(bc)

            # Update active product with merged barcodes
            merged_barcodes = ";".join(sorted(all_barcodes))
            self.update_product(active_product_id, {
                                'barcode': merged_barcodes})

            # Set deleted and linked_items on all linked products
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for pid in products_to_link:
                if hasattr(pid, 'item'):
                    pid = pid.item()
                else:
                    pid = int(pid)

                if pid != active_product_id:  # Don't mark the active product as deleted
                    self.update_product(pid, {
                        'linked_items': str(active_product_id),
                        'deleted': timestamp
                    })

            # ========== DEBUG: Print all affected rows ==========
            self._print_link_debug(active_product_id, products_to_link)
            # ====================================================

            return True, f"Successfully linked {len(products_to_link)} products to product {active_product_id}"

        except Exception as e:
            print(f"Error linking products: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Error: {str(e)}"

    def _print_link_debug(self, active_product_id, linked_product_ids):
        """Print debug info showing all affected products after linking"""
        print("\n" + "=" * 80)
        print("DEBUG: Database state after linking products")
        print("=" * 80)

        # Collect all IDs to query
        all_ids = set([active_product_id] + [int(pid) if hasattr(pid,
                      'item') else int(pid) for pid in linked_product_ids])
        placeholders = ", ".join(["?" for _ in all_ids])

        # Query the affected rows
        df = self.con.execute(f"""
            SELECT id, name_search, brands_search, barcode, active, deleted, linked_items
            FROM products 
            WHERE id IN ({placeholders})
        """, list(all_ids)).df()

        # Print active product
        print("\n📗 ACTIVE PRODUCT (master):")
        print("-" * 80)
        active_row = df[df['id'] == active_product_id]
        if not active_row.empty:
            row = active_row.iloc[0]
            print(f"  ID:           {row['id']}")
            print(f"  Name:         {row['name_search']}")
            print(f"  Brand:        {row['brands_search']}")
            print(f"  Barcode:      {row['barcode']}")
            print(f"  Active:       {row['active']}")
            print(f"  Deleted:      {row['deleted']}")
            print(f"  Linked Items: {row['linked_items']}")

        # Print linked products (deleted)
        linked_rows = df[df['id'] != active_product_id]
        if not linked_rows.empty:
            print(
                f"\n📕 LINKED PRODUCTS (marked as deleted): {len(linked_rows)} products")
            print("-" * 80)
            for _, row in linked_rows.iterrows():
                print(f"\n  ID:           {row['id']}")
                print(f"  Name:         {row['name_search']}")
                print(f"  Brand:        {row['brands_search']}")
                print(f"  Barcode:      {row['barcode']}")
                print(f"  Active:       {row['active']}")
                print(f"  Deleted:      {row['deleted']}")
                print(f"  Linked Items: {row['linked_items']}")

        print("\n" + "=" * 80)
        print("END DEBUG")
        print("=" * 80 + "\n")

    def activate_product(self, product_id, updates=None):
        """
        Activate a product (set active = 1) and optionally update fields

        Args:
            product_id: Product ID to activate
            updates: Optional dictionary of field updates

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if hasattr(product_id, 'item'):
                product_id = product_id.item()
            else:
                product_id = int(product_id)

            all_updates = updates.copy() if updates else {}
            all_updates['active'] = 1

            success = self.update_product(product_id, all_updates)

            if success:
                # ========== DEBUG: Print activated product ==========
                self._print_activate_debug(product_id)
                # ====================================================
                return True, f"Product {product_id} has been activated successfully"
            else:
                return False, f"Failed to activate product {product_id}"

        except Exception as e:
            print(f"Error activating product {product_id}: {str(e)}")
            return False, f"Error: {str(e)}"

    def _print_activate_debug(self, product_id):
        """Print debug info showing activated product"""
        print("\n" + "=" * 80)
        print("DEBUG: Product activated")
        print("=" * 80)

        # Query the activated product
        df = self.con.execute("""
            SELECT id, name_search, brands_search, barcode, active, deleted, linked_items,
                   energy, protein, fat, saturated_fatty_acid, carbohydrates, sugar, salt
            FROM products 
            WHERE id = ?
        """, [product_id]).df()

        if not df.empty:
            row = df.iloc[0]
            print(f"\n📗 NEWLY ACTIVATED PRODUCT:")
            print("-" * 80)
            print(f"  ID:           {row['id']}")
            print(f"  Name:         {row['name_search']}")
            print(f"  Brand:        {row['brands_search']}")
            print(f"  Barcode:      {row['barcode']}")
            print(f"  Active:       {row['active']} ← NOW ACTIVE!")
            print(f"  Deleted:      {row['deleted']}")
            print(f"  Linked Items: {row['linked_items']}")
            print(f"  --- Nutrition ---")
            print(f"  Energy:       {row['energy']}")
            print(f"  Protein:      {row['protein']}")
            print(f"  Fat:          {row['fat']}")
            print(f"  Sat. Fat:     {row['saturated_fatty_acid']}")
            print(f"  Carbs:        {row['carbohydrates']}")
            print(f"  Sugar:        {row['sugar']}")
            print(f"  Salt:         {row['salt']}")

        print("\n" + "=" * 80)
        print("END DEBUG")
        print("=" * 80 + "\n")

    def close(self):
        """Close database connection"""
        self.con.close()
