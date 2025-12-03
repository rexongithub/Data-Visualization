"""
Database operations for the Food Product Similarity Dashboard
"""
import duckdb
import pandas as pd
import os
from config import DATABASE_PATH, CSV_FILENAME


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
                df_temp = pd.read_csv(csv_path)
                
                if 'deleted' in df_temp.columns:
                    df_temp = df_temp[df_temp["deleted"].isna()]
                
                print(f"Loaded {len(df_temp)} rows from CSV")
                self.con.execute("CREATE TABLE products AS SELECT * FROM df_temp")
                
                result = self.con.execute("SELECT COUNT(*) as count FROM products").fetchone()
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
                (1, 'Apple Juice', 'Beverage', 45, 0.2, 0.0, 1),
                (2, 'Orange Juice', 'Beverage', 50, 0.3, 0.1, 0),
                (3, 'Tomato Soup', 'Soup', 80, 2.0, 3.5, 0)
            ) AS t(id, name, categories, energy, protein, fat, active)
        """)
        print("Sample products table created")
    
    def _create_empty_table(self):
        """Create empty products table"""
        self.con.execute("""
            CREATE TABLE products (
                id INTEGER,
                name VARCHAR,
                categories VARCHAR,
                energy DOUBLE,
                protein DOUBLE,
                fat DOUBLE,
                active INTEGER
            )
        """)
        print("Created empty products table due to error")
    
    def get_filtered_products(self, active_filter):
        """
        Get products filtered by active status
        
        Args:
            active_filter: "all", "1" (active), or "0" (inactive)
        
        Returns:
            pandas DataFrame with filtered products
        """
        try:
            if active_filter == "1":
                query = "SELECT * FROM products WHERE active = 1"
            elif active_filter == "0":
                query = "SELECT * FROM products WHERE active = 0"
            else:
                query = "SELECT * FROM products"
            
            return self.con.execute(query).df().reset_index(drop=True)
        except Exception as e:
            print(f"Error filtering data: {str(e)}")
            return pd.DataFrame()
    
    def get_product_by_id(self, product_id):
        """
        Get a single product by ID
        
        Args:
            product_id: Product ID to retrieve
        
        Returns:
            pandas Series with product data
        """
        try:
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
    
    def close(self):
        """Close database connection"""
        self.con.close()